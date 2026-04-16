# Cred-ible Backend

This backend service is built with FastAPI and provides credit scoring, authentication, model training, and marketplace offer APIs.

## Local setup

1. Open a terminal in `backend`
2. Create a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the API server:
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

## Training the model

Use the training script to build or refresh the model from Excel data.

```powershell
python train_model.py --dataset ..\credit_demo_dataset.xlsx
```

## Health check

- `http://127.0.0.1:8000/health`
