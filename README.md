# Cred-ible

This repository contains two main services:

- `backend` – FastAPI service for credit scoring, authentication, model training, and marketplace offer APIs.
- `frontend` – Next.js app for the Cred-ible user experience.

## Run locally

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Then browse the app at `http://localhost:3000`.

## Notes

- The frontend uses `NEXT_PUBLIC_API_BASE_URL` to connect to `http://127.0.0.1:8000` by default.
- The `frontend_loan_extracted` folder contains legacy UI extraction content and is not required for the main app.
