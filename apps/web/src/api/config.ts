export const API_BASE = '/api/v1'

// Single bearer token guarding the control plane. For a you-only tool over
// Tailscale this can live in the client; override with VITE_API_TOKEN.
export const API_TOKEN = import.meta.env.VITE_API_TOKEN ?? 'dev-token'
