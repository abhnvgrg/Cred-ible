# BharatCredit Frontend

This is the Next.js frontend for the BharatCredit application.

## Local development

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open the app at `http://localhost:3000`.

## Available commands

- `npm run dev` — start the local development server
- `npm run clean` — delete the `.next` build cache
- `npm run dev:clean` — clean cache then start dev server
- `npm run build` — create a production build
- `npm run preview` — preview the production build locally
- `npm run lint` — run Next.js lint checks

## Environment variables

Use `frontend/.env.example` to create `frontend/.env.local`.

- `NEXT_PUBLIC_API_BASE_URL` — base URL for the backend API (default: `http://127.0.0.1:8000`)
