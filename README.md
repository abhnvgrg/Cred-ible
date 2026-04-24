# cred-ible 🇮🇳

> **Unlock trust for India's credit-invisible borrowers.**

cred-ible is an AI-powered alternative credit scoring engine that translates UPI transaction behaviour, bill repayment discipline, and GST compliance into a fast, explainable lending decision. Built for freelancers, gig workers, street merchants, and micro-entrepreneurs who have real financial activity but no formal credit trail.

**Live Demo:** [cred-ible.vercel.app](https://cred-ible.vercel.app)

---

## The Problem

Over 400 million working Indians are effectively **credit-invisible** — not because they're risky, but because conventional bureau scores (CIBIL, Experian) only see EMI repayments and credit card history. A street vendor who pays rent on time every month, runs ₹80,000/month through UPI, and files GST diligently still shows up as *No Score*.

cred-ible fixes that.

---

## How It Works

```
Applicant Data (UPI + Bureau + Alternate)
         │
         ▼
┌─────────────────────────┐
│   cred-ible Engine      │  ← ML model trained on 50,000 synthetic borrowers
│   (FastAPI Backend)     │    with CIBIL-style + alternate data features
└─────────┬───────────────┘
          │  Logic Score (300–900)
          ▼
┌─────────────────────────┐
│   Loan Marketplace      │  ← Matched lender offers based on score band
│   + What-If Simulator   │  ← "What if I reduce my credit utilisation?"
└─────────────────────────┘
```

---

##  Key Features

| Feature | Description |
|---|---|
| **Logic Score Engine** | Generates a 300–900 score using UPI activity, GST compliance, utility & mobile bill history — not just bureau data |
| **Real-Time Decisions** | End-to-end processing under 1.2 seconds per applicant |
| **AI Processing Agents** | Live agent pipeline: Income Agent → Repayment Agent → Lifestyle Agent → Compliance Agent |
| **What-If Simulator** | Predicts score impact of behavioural changes (e.g. reducing credit utilisation, paying bills on time) |
| **Loan Marketplace** | Connects scored applicants to matched lender offers (SBI, HDFC, Bajaj Finserv, etc.) |
| **NTC Borrower Support** | New-to-Credit applicants scored entirely on alternate data — no bureau history required |
| **Offline Fallback** | Decision layer stays active even when third-party APIs are unresponsive |
| **RBI-Compliant Output** | Scores are decision-support insights, designed for use alongside lender underwriting |

---

##  Technology Stack

### Frontend
- **Framework:** [Next.js 14](https://nextjs.org/) — App Router, Server Components
- **UI Library:** [React 18](https://react.dev/)
- **Styling:** [TailwindCSS](https://tailwindcss.com/)
- **Language:** TypeScript

### Backend
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
- **Language:** Python 3.10+
- **ML Runtime:** Custom risk prediction models (scikit-learn / XGBoost)
- **Server:** Uvicorn

### Data & ML
- Training datasets included in repo root (`1000bor.csv`, `50kborr.csv`, `credit_demo_dataset.xlsx`)
- Business credit demo dataset: `credit_score_demo_100b_5yr.xlsx` (100 businesses, 5-year view)
- Model targets: **credit score** (regression, 300–900) + **loan decision** (4-class classification)

---

##  Repository Structure

```
cred-ible/
├── backend/                        # FastAPI backend service
│   ├── app/
│   │   ├── main.py                 # Entry point, route registration
│   │   ├── routes/                 # API route handlers (score, auth, marketplace, offers)
│   │   ├── agents/                 # AI agent pipeline (income, repayment, lifestyle, compliance)
│   │   ├── models/                 # ML model loading & inference
│   │   └── schemas/                # Pydantic request/response schemas
│   ├── train_model.py              # Model training script
│   └── requirements.txt            # Python dependencies
│
├── frontend/                       # Next.js web application
│   ├── app/                        # App Router: pages, layouts, server components
│   ├── components/                 # Reusable UI components
│   └── public/                     # Static assets
│
├── frontend_loan_extracted/
│   └── stitch_remix_of_ai_credit_scoring_ui/  # Legacy UI extraction (reference only)
│
├── 1000bor.csv                     # 1,000-borrower training dataset (CSV)
├── 1000bor.xlsx                    # 1,000-borrower training dataset (Excel)
├── 50kborr.csv                     # 50,000-borrower training dataset (CSV) ← primary
├── credit_demo_dataset.xlsx        # Demo dataset for quick model testing
├── credit_score_demo_100b\_5yr.xlsx # Business credit demo: 100 SMEs across 5 years
├── credible_screens.zip            # UI screenshots
├── .gitignore
├── package.json
└── README.md
```

---

##  Getting Started

### Prerequisites

- Node.js v18+
- Python 3.10+
- npm or yarn

---

### 1. Clone the Repository

```bash
git clone https://github.com/abhnvgrg/Cred-ible.git
cd Cred-ible
```

---

### 2. Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend will be live at `http://127.0.0.1:8000`.  
Check the health endpoint: `http://127.0.0.1:8000/health`  
Interactive API docs: `http://127.0.0.1:8000/docs`

---

### 3. Frontend Setup

Open a new terminal from the repo root:

```bash
cd frontend

# Install dependencies
npm install

# Copy environment config
cp .env.example .env.local
# (The default config points to http://127.0.0.1:8000)

# Start the dev server
npm run dev
```

The frontend will be live at `http://localhost:3000`.

---

##  Model Training

cred-ible's ML model predicts credit risk (Low / Medium / High) and outputs a Logic Score from 300–900.

To train or retrain the model locally using the included datasets:

```bash
cd backend

# Train on the 50k borrower dataset (recommended)
python train_model.py --dataset ../50kborr.csv

# Or train on the demo Excel dataset
python train_model.py --dataset ../credit_demo_dataset.xlsx

# Train on business credit data (SME model)
python train_model.py --dataset ../credit_score_demo_100b_5yr.xlsx --mode business
```

### Key Input Features

The model uses **50 features** across six categories:

| Category | Examples |
|---|---|
| **Bureau / Credit History** | credit_utilization_pct, num_defaults, missed_payments_24m, credit_mix_score |
| **Alternate Data ★** | upi_monthly_txn_count, mobile_bill_ontime_pct, utility_bill_ontime_pct, gst_compliance_score |
| **Income & Employment** | monthly_income_inr, employment_type, work_experience_years |
| **Financial Behaviour** | savings_rate_pct, bank_balance_avg_3m, debt_to_income_ratio |
| **Loan Request** | loan_amount_requested_inr, loan_tenure_months, loan_to_income_ratio |
| **Demographics** | age, state, residence_type, education_level |

> ★ Alternate data columns are the core differentiator — they enable scoring of New-to-Credit (NTC) borrowers who have zero bureau history.

### Model Targets

| Target | Type | Values |
|---|---|---|
| `credit_score` | Regression | 300 – 900 |
| `loan_decision` | Classification (4-class) | Approved / Conditionally Approved / Under Review / Rejected |

---

## 🔌 API Reference

Base URL: `http://127.0.0.1:8000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `POST` | `/score` | Submit applicant data, receive Logic Score + decision |
| `POST` | `/score/simulate` | What-If simulation — predict score under changed inputs |
| `GET` | `/marketplace/offers` | Fetch matched lender offers for a given score |
| `POST` | `/auth/login` | User authentication |
| `POST` | `/train` | Trigger model retraining (authenticated) |

Full interactive docs at `/docs` (Swagger UI) or `/redoc`.

---

##  AI Agent Pipeline

When an applicant is scored, cred-ible runs a four-agent analysis pipeline:

```
1. Income Agent        → Validates income signals (UPI flow vs declared income)
2. Repayment Agent     → Analyses bill payment history and DPD flags
3. Lifestyle Agent     → Interprets spending patterns and savings behaviour
4. Compliance Agent    → Checks GST filing regularity for business applicants
```

Each agent contributes a sub-score that feeds into the final Logic Score, and produces an explainable reason code visible in the UI.

---

##  Datasets

| File | Rows | Description |
|---|---|---|
| `1000bor.csv` / `.xlsx` | 1,000 | Initial training dataset |
| `50kborr.csv` | 50,000 | Primary training dataset (50 features, 2 targets) |
| `credit_demo_dataset.xlsx` | ~100 | Quick demo / smoke-test dataset |
| `credit_score_demo_100b_5yr.xlsx` | ~500 | Business credit: 100 SMEs × 5 years |

The 50k dataset includes realistic distributions across employment types (Salaried, Gig Worker, Business Owner, Freelancer, etc.), Indian states, and borrower segments including **10,795 NTC borrowers** scored on alternate data only.

---

##  Disclaimer & RBI Compliance

cred-ible outputs are **decision-support insights** and must be combined with full lender underwriting under prevailing [RBI digital lending guidelines](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=54178).

- Demo and assessment inputs may be retained for up to 30 days for audit, grievance resolution, and model monitoring purposes.
- This platform does not constitute a credit bureau or a regulated NBFC/bank.
- All training data used in this repository is **synthetic** and does not contain real personal financial information.

---

##  Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request


---

<div align="center">
   <a href="https://cred-ible.vercel.app">cred-ible.vercel.app</a>
</div>
