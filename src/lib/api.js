// Vercel routes /api to FastAPI on the same deployment, including previews.
export const API_BASE = (import.meta.env.VITE_API_URL?.trim() || (import.meta.env.DEV ? 'http://localhost:8000' : '/api')).replace(/\/+$/, '');
