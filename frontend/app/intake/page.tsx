"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import type { BorrowerSignalInput, ParseStatementResult } from "@/lib/scoring";
import { saveIntakePayload, saveParsedStatementResult } from "@/lib/scoring";

type EmploymentTypeUi = "salaried" | "freelance" | "self_employed" | "gig_worker" | "business_owner";

function normalizeEmployment(type: EmploymentTypeUi): BorrowerSignalInput["employment"]["employment_type"] {
  if (type === "salaried") return "salaried";
  if (type === "freelance") return "freelance";
  return "self_employed";
}

function toRatio(percentage: number): number {
  return Math.max(0, Math.min(1, percentage / 100));
}

function buildBorrowerPayloadFromParsed(
  parsed: ParseStatementResult["parsed_signals"],
  borrowerName: string,
  employmentType: EmploymentTypeUi,
  gstApplicable: boolean
): BorrowerSignalInput {
  const utilityRatio = toRatio(parsed.utility_bill_ontime_pct);
  const rentOnTime = Math.max(0.5, Math.min(0.99, utilityRatio * 0.92));
  const monthlyIncome = Math.max(0, Math.round(parsed.monthly_income_inr));
  const monthsHistory = Math.max(1, Math.round(parsed.months_of_history));
  const gstSignal = gstApplicable
    ? {
        filing_frequency: "monthly" as const,
        filing_consistency_score: Math.max(0, Math.min(1, utilityRatio)),
        missed_filings_last_12m: utilityRatio < 0.7 ? 2 : utilityRatio < 0.85 ? 1 : 0,
        revenue_trend_pct: parsed.monthly_volume_trend_pct,
        is_applicable: true
      }
    : {
        filing_frequency: "not_applicable" as const,
        filing_consistency_score: 0,
        missed_filings_last_12m: 0,
        revenue_trend_pct: 0,
        is_applicable: false
      };

  return {
    borrower_name: borrowerName,
    upi: {
      transaction_frequency_per_month: Math.max(0, Math.round(parsed.upi_monthly_txn_count)),
      average_transaction_value_inr: Math.max(0, parsed.upi_avg_txn_value),
      merchant_diversity_score: Math.max(0, Math.min(1, parsed.merchant_diversity_score)),
      regularity_score: Math.max(0, Math.min(1, parsed.regularity_score)),
      months_of_history: monthsHistory,
      monthly_volume_trend_pct: parsed.monthly_volume_trend_pct
    },
    gst: gstSignal,
    rent: {
      rent_amount_inr: Math.max(0, Math.round(monthlyIncome * 0.22)),
      on_time_payment_ratio: rentOnTime,
      late_payments_last_24m: rentOnTime < 0.8 ? 3 : rentOnTime < 0.9 ? 1 : 0,
      tenancy_months: Math.max(3, Math.min(120, monthsHistory)),
      longest_gap_months: parsed.regularity_score < 0.4 ? 2 : 0
    },
    mobile: {
      recharge_frequency_per_month: Math.max(0, parsed.mobile_recharge_freq),
      average_recharge_value_inr: Math.max(149, Math.round(parsed.upi_avg_txn_value * 0.45)),
      consistency_score: Math.max(0, Math.min(1, parsed.recharge_consistency_score)),
      finance_app_usage_score: Math.max(0.35, Math.min(0.95, parsed.merchant_diversity_score + 0.2)),
      risky_app_usage_score: Math.max(0.05, Math.min(0.6, 1 - parsed.regularity_score)),
      monthly_data_usage_gb: Math.max(8, Math.round(parsed.mobile_recharge_freq * 8))
    },
    utilities: {
      electricity_on_time_ratio: utilityRatio,
      water_on_time_ratio: Math.max(0, Math.min(1, utilityRatio * 0.96)),
      average_monthly_total_inr: Math.max(300, Math.round(monthlyIncome * 0.06)),
      payment_months_observed: monthsHistory
    },
    employment: {
      employment_type: normalizeEmployment(employmentType),
      monthly_income_inr: monthlyIncome,
      income_stability_score: Math.max(0, Math.min(1, parsed.income_stability_score)),
      months_in_current_work: monthsHistory,
      income_proof_type: "bank_statement"
    },
    existing_emi_on_time_ratio: Math.max(0, Math.min(1, 1 - parsed.debt_to_income_ratio * 0.35)),
    declared_attributes: {}
  };
}

export default function IntakePage() {
  const router = useRouter();
  const [borrowerName, setBorrowerName] = useState("");
  const [employmentType, setEmploymentType] = useState<EmploymentTypeUi>("self_employed");
  const [gstApplicable, setGstApplicable] = useState(false);
  const [loanAmountRequested, setLoanAmountRequested] = useState(120000);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fileLabel = useMemo(() => {
    if (!selectedFile) return "No file selected";
    const sizeKb = Math.max(1, Math.round(selectedFile.size / 1024));
    return `${selectedFile.name} (${sizeKb} KB)`;
  }, [selectedFile]);

  const submitStatement = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    if (!borrowerName.trim()) {
      setError("Full name is required.");
      return;
    }
    if (!selectedFile) {
      setError("Please upload a PDF or CSV statement.");
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("borrower_name", borrowerName.trim());
      formData.append("employment_type", normalizeEmployment(employmentType));
      formData.append("gst_applicable", gstApplicable ? "true" : "false");
      formData.append("loan_amount_requested", String(Math.max(0, loanAmountRequested)));

      const parsed = await apiFetch<ParseStatementResult>("/parse/statement", {
        method: "POST",
        body: formData,
        timeoutMs: 4000
      });

      const payload = buildBorrowerPayloadFromParsed(
        parsed.parsed_signals,
        borrowerName.trim(),
        employmentType,
        gstApplicable
      );
      const wasSaved = saveIntakePayload(payload);
      if (!wasSaved) {
        setError("Unable to cache parsed intake in this browser.");
        return;
      }
      saveParsedStatementResult(parsed);
      router.push("/ai-processing?source=intake");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to parse statement.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const useDemoStatement = () => {
    router.push("/ai-processing?persona=raju&source=demo");
  };

  return (
    <div className="space-y-6">
      <SurfaceCard>
        <span className="eyebrow">Upload-first intake</span>
        <h1 className="headline mt-4 text-4xl font-extrabold">Upload bank statement to start scoring</h1>
        <p className="mt-2 text-sm muted">
          Only basic borrower details are needed. Cred-ible derives behavioral signals automatically from statement transactions.
        </p>
      </SurfaceCard>

      <form className="space-y-5" onSubmit={submitStatement}>
        <SurfaceTile>
          <h2 className="headline text-xl font-bold">Step 1 — Basic info</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="form-label">
              Full name
              <input
                className="form-input"
                value={borrowerName}
                onChange={(event) => setBorrowerName(event.target.value)}
                placeholder="e.g. Raju Kumar"
                required
              />
            </label>
            <label className="form-label">
              Employment type
              <select
                className="form-select"
                value={employmentType}
                onChange={(event) => setEmploymentType(event.target.value as EmploymentTypeUi)}
              >
                <option value="salaried">Salaried</option>
                <option value="freelance">Freelancer</option>
                <option value="self_employed">Self-employed</option>
                <option value="gig_worker">Gig worker</option>
                <option value="business_owner">Business owner</option>
              </select>
            </label>
            <label className="form-label">
              GST registered?
              <select
                className="form-select"
                value={gstApplicable ? "yes" : "no"}
                onChange={(event) => setGstApplicable(event.target.value === "yes")}
              >
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </label>
            <label className="form-label">
              Loan amount requested (INR)
              <input
                className="form-input"
                type="number"
                min={0}
                value={loanAmountRequested}
                onChange={(event) => setLoanAmountRequested(Number(event.target.value || 0))}
              />
            </label>
          </div>
        </SurfaceTile>

        <SurfaceTile>
          <h2 className="headline text-xl font-bold">Step 2 — Statement upload</h2>
          <div className="mt-4 rounded-2xl border border-dashed border-outline-variant/50 bg-surface-low/80 p-5">
            <p className="text-sm font-semibold text-slate-100">Upload your bank statement (PDF or CSV)</p>
            <p className="mt-1 text-xs muted">Supported banks: SBI, HDFC, Axis, ICICI. Other banks are also supported.</p>
            <input
              className="mt-4 form-input"
              type="file"
              accept=".pdf,.csv,application/pdf,text/csv"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
            <p className="mt-2 text-xs muted">{fileLabel}</p>
            <button type="button" className="btn-ghost mt-3 text-sm" onClick={useDemoStatement}>
              Use demo statement (Raju)
            </button>
          </div>
        </SurfaceTile>

        {error ? (
          <SurfaceTile className="border border-red-500/35 bg-red-500/10">
            <p className="text-sm text-red-200">{error}</p>
          </SurfaceTile>
        ) : null}

        <div className="flex flex-wrap gap-3">
          <button type="submit" className="btn-primary text-sm" disabled={isSubmitting}>
            {isSubmitting ? "Parsing statement..." : "Start AI processing"}
          </button>
          <ActionLink href="/persona-selection" variant="secondary" className="text-sm">
            Persona demo
          </ActionLink>
        </div>
      </form>

      <RbiNotice
        disclaimer="Cred-ible outputs are decision-support insights and should be combined with lender underwriting controls."
        retention="Data retention: uploaded files and derived signals may be retained for up to 30 days for audit and model monitoring."
      />
    </div>
  );
}
