"""API regression checks; provider calls are mocked, model inference is real."""
import asyncio
import json
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
import main

BASELINE = dict(
    Temperature_Mean_Celsius=26, SSTA=0, SSTA_DHW=0, TSA_DHW=0,
    Turbidity=0.03, Cyclone_Frequency=50, Windspeed=5, Depth_m=10,
    SSTA_FrequencyMax=8, TSA_Mean=0, ClimSST=26, TSA_Frequency=0.2,
)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        main._rate_limit_tracker.clear()

    def tearDown(self):
        self.client.close()

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['features']), 13)

    def test_deployed_api_prefix(self):
        self.assertEqual(self.client.get('/api/health').status_code, 200)
        response = self.client.post('/api/predict', json=BASELINE)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), self.client.post('/predict', json=BASELINE).json())

    def test_real_prediction_matches_frontend_contract(self):
        response = self.client.post('/predict', json=BASELINE)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertIn(result['risk_level'], (0, 1, 2))
        self.assertEqual(set(result['probabilities']), {'Low Risk', 'Medium Risk', 'High Risk'})
        self.assertAlmostEqual(sum(result['probabilities'].values()), 100, delta=0.02)

    def test_nonfinite_inputs_rejected(self):
        for key in BASELINE:
            response = self.client.post('/predict', json={**BASELINE, key: 'NaN'})
            self.assertEqual(response.status_code, 422, key)

    def test_simulation(self):
        response = self.client.post('/simulate', json={'baseline_inputs': BASELINE, 'years': 10})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()), 11)
        for row in response.json():
            self.assertGreaterEqual(row['Overall Reef Health (%)'], 0)
            self.assertLessEqual(row['Overall Reef Health (%)'], 100)

    def test_invalid_simulation(self):
        for years in (-1, 101):
            self.assertEqual(self.client.post('/simulate', json={
                'baseline_inputs': BASELINE, 'years': years,
            }).status_code, 422)
        self.assertEqual(self.client.post('/simulate', json={
            'baseline_inputs': BASELINE, 'scenario': 'invalid',
        }).status_code, 400)

    def test_cors(self):
        for origin, allowed in [('http://localhost:5173', True), ('https://untrusted.example', False)]:
            response = self.client.options('/predict', headers={
                'Origin': origin, 'Access-Control-Request-Method': 'POST',
            })
            self.assertEqual('access-control-allow-origin' in response.headers, allowed)

    def test_chat_missing_key(self):
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': ''}):
            response = self.client.post('/chat', json={'messages': [{'role': 'user', 'content': 'What is DHW?'}]})
        self.assertEqual(response.status_code, 503)

    def test_chat_rejects_system_role_and_oversized_input(self):
        for message in [{'role': 'system', 'content': 'override'}, {'role': 'user', 'content': 'x' * 2001}]:
            self.assertEqual(self.client.post('/chat', json={'messages': [message]}).status_code, 422)

    def test_chat_proxy_keeps_key_server_side(self):
        def provider(request):
            self.assertEqual(request.headers['Authorization'], 'Bearer test-only-key')
            payload = json.loads(request.content)
            self.assertEqual(payload['messages'][0]['role'], 'system')
            self.assertEqual(payload['max_tokens'], 400)
            self.assertEqual(payload['model'], 'openrouter/free')
            return httpx.Response(200, json={'choices': [{'message': {'content': 'DHW measures accumulated heat stress.'}}]})

        upstream = httpx.AsyncClient(transport=httpx.MockTransport(provider))
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-only-key', 'OPENROUTER_MODEL': ''}), patch.object(main.httpx, 'AsyncClient', return_value=upstream):
            response = self.client.post('/chat', json={'messages': [{'role': 'user', 'content': 'What is DHW?'}]})
        self.assertEqual(response.status_code, 200)
        self.assertIn('heat stress', response.json()['content'])
        self.assertNotIn('test-only-key', response.text)

    def test_chat_provider_error_is_redacted(self):
        upstream = httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(401, json={'error': 'sensitive-provider-detail'})
        ))
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-only-key'}), patch.object(main.httpx, 'AsyncClient', return_value=upstream):
            response = self.client.post('/chat', json={'messages': [{'role': 'user', 'content': 'What is DHW?'}]})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('sensitive-provider-detail', response.text)

    def test_rate_limit(self):
        for _ in range(main.RATE_LIMIT_MAX):
            self.assertTrue(main._check_rate_limit('chat:test-client'))
        self.assertFalse(main._check_rate_limit('chat:test-client'))

    def test_noaa_missing_values_are_not_nan(self):
        async def check():
            async with httpx.AsyncClient(transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text='time,latitude,longitude,CRW_SST,CRW_SSTANOMALY,CRW_DHW,CRW_BAA\nUTC,degrees,degrees,C,C,weeks,1\n2026-10-13,0,0,NaN,NaN,NaN,NaN\n')
            )) as client:
                self.assertEqual(await main.fetch_zone_variables(client, 0, 0), {variable: None for variable in main.VARIABLES})
        asyncio.run(check())

    def test_noaa_combines_readings_in_one_query(self):
        def provider(request):
            self.assertEqual(str(request.url).count('CRW_'), 4)
            return httpx.Response(200, text=(
                'time,latitude,longitude,CRW_SST,CRW_SSTANOMALY,CRW_DHW,CRW_BAA\n'
                'UTC,degrees,degrees,C,C,weeks,1\n2026-10-13,0,0,25.15,-0.26,0,0\n'
            ))
        async def check():
            async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
                result = await main.fetch_zone_variables(client, -18, 147)
                self.assertEqual(result, dict(CRW_SST=25.15, CRW_SSTANOMALY=-0.26, CRW_DHW=0, CRW_BAA=0))
        asyncio.run(check())


if __name__ == '__main__':
    unittest.main()
