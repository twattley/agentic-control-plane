# apps/web — React 19 + Vite

## Stack

- **React 19** + **TypeScript**
- **Vite** — dev server on :5400, proxies `/api` → :8400
- **TanStack Query v5** — server state
- **Tailwind CSS** — utility classes
- **React Router v7** — client-side routing

## Source layout

```
src/
  api/
    config.ts       API_BASE constant
    http.ts         apiFetch / apiPost / apiPut / apiDelete
    queryClient.ts  singleton QueryClient
    ApiProvider.tsx QueryClientProvider wrapper
    hooks.ts        TanStack Query hooks per resource
  features/         one folder per domain feature
  components/       shared UI components
  App.tsx
  main.tsx
  index.css
```

## Commands

```bash
make web           # dev server on :5400
npm run build      # production build (from apps/web/)
```
