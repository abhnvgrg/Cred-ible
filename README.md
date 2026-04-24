# cred-ible 🇮🇳

**Unlock trust for India's credit-invisible borrowers.**

cred-ible is an alternative credit scoring engine that translates transaction behavior, repayment discipline, and compliance patterns into a fast lending decision layer. Built to serve freelancers, street merchants, and micro-entrepreneurs who lack traditional credit histories, this platform leverages ML models backed by FastAPI and a modern frontend to deliver lightning-fast underwriting decisions.

![Dashboard Preview](https://via.placeholder.com/1200x600?text=cred-ible+Dashboard+Preview)

## 🌟 Key Features

- **Cred-ible Engine**: Process alternative data (UPI, GST, utility payments) in real-time to generate a 'Logic Score'.
- **Real-Time Analysis**: Processing latency of under 1.2s for instantaneous borrowing decisions.
- **What-If Simulator**: Advanced journey tool for predicting how changes in cash flow or behavior affect credit risk.
- **Loan Marketplace**: Directly connects evaluated users with customized loan offers based on their generated logic score.
- **AI Processing Agents**: Live agent-based demo runs (income, repayment, lifestyle, and compliance analysis).
- **Parallel Specialist Orchestration**: Income, repayment, lifestyle, and compliance specialists are dispatched concurrently, with optional LLM-backed specialist execution.
- **Offline Fallback Continuity**: Keeps the decision layer active even when various third-party APIs are unresponsive.

## 🛠️ Technology Stack

**Frontend**
- **Framework**: [Next.js](https://nextjs.org/) (App Router, Server Components)
- **Library**: [React 18](https://react.dev/)
- **Styling**: [TailwindCSS](https://tailwindcss.com/)
- **Language**: TypeScript

**Backend**
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Language**: Python 3.10+
- **Orchestration**: Parallel specialist orchestration engine (rule-based by default, LLM-enabled via environment variables)
- **Machine Learning**: Custom ML risk prediction models (trained via Excel datasets) for `/model/*` endpoints
- **Server**: Uvicorn

## 🚀 Getting Started

Follow these instructions to set up the project locally. 

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- npm or yarn

### 1. Backend Setup

Open a terminal and navigate to the `backend` directory.

```powershell
cd backend

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment (Windows)
.\.venv\Scripts\Activate.ps1
# On macOS/Linux use: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
*(The backend will be available at `http://127.0.0.1:8000`. You can test by navigating to the `/health` endpoint.)*

### 2. Frontend Setup

Open a new terminal and navigate to the `frontend` directory.

```powershell
cd frontend

# Install Node dependencies
npm install

# Setup environment variables
copy .env.example .env.local

# Run the development server
npm run dev
```
*(The frontend will be available at `http://localhost:3000`.)*

## 🧠 Model Training

cred-ible uses an integrated machine learning model that predicts risk based on applicant data (low, medium, high). 

To build or refresh the model locally based on demo data (found in the root directory like `credit_demo_dataset.xlsx`), run the following script from the `backend` directory:

```powershell
python train_model.py --dataset ..\credit_demo_dataset.xlsx
```

## 🤖 Parallel LLM Orchestration (Optional)

By default, scoring uses parallel rule-based specialists. To enable LLM-dispatched parallel specialists for the primary `/score` flow, configure:

```powershell
$env:CREDIBLE_LLM_ORCHESTRATION="true"
$env:CREDIBLE_LLM_API_KEY="your_api_key"
$env:CREDIBLE_LLM_MODEL="gpt-4.1-mini"
$env:CREDIBLE_LLM_ENDPOINT="https://api.openai.com/v1/chat/completions"
$env:CREDIBLE_LLM_TIMEOUT_SECONDS="14"
```

You can verify active orchestration mode at:

- `GET /orchestration/status`

## 📁 Repository Structure

```
cred-ible/
├── backend/                   # FastAPI backend service
│   ├── app/                   # API routes, Agents, ML handlers, and Schemas
│   ├── train_model.py         # ML model training script
│   └── requirements.txt       # Python dependencies
├── frontend/                  # Next.js web application
│   ├── app/                   # Next.js App Router structure (Pages & Layouts)
│   ├── components/            # Reusable UI components & Primitives
│   └── public/                # Static assets
├── README.md                  # Project documentation (You are here)
└── credit_demo_dataset.xlsx   # Sample dataset for model training
```

## ⚖️ Disclaimer & RBI Compliance

*cred-ible outputs are decision-support insights and must be combined with full lender underwriting under prevailing RBI (Reserve Bank of India) digital lending guidance. Demo and assessment inputs may be retained for up to 30 days for audits, grievance resolution, and model monitoring.*

---
**Made with ❤️ for Hackathon-08**
