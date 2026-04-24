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

## Parallel specialist orchestration

The scoring pipeline dispatches income, repayment, lifestyle, and compliance specialists concurrently.

- Default mode: `rules_parallel`
- Optional mode: `llm_parallel` when LLM environment variables are configured

Set these environment variables to enable LLM-backed specialists:

```powershell
$env:CREDIBLE_LLM_ORCHESTRATION="true"
$env:CREDIBLE_LLM_API_KEY="your_api_key"
$env:CREDIBLE_LLM_MODEL="gpt-4.1-mini"
$env:CREDIBLE_LLM_ENDPOINT="https://api.openai.com/v1/chat/completions"
$env:CREDIBLE_LLM_TIMEOUT_SECONDS="14"
```

Inspect runtime mode:

- `GET /orchestration/status`

## Health check

- `https://cred-ible.onrender.com/health`
