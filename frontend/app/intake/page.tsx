"use client";

import type { FormEvent, ReactNode } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ActionLink, RbiNotice, SurfaceCard } from "@/components/ui/primitives";
import type { BorrowerSignalInput, GSTSignal } from "@/lib/scoring";
import { saveIntakePayload } from "@/lib/scoring";

interface IntakeFormState {
  borrower_name: string;
  notes: string;
  existing_emi_on_time_ratio: number;
  upi: BorrowerSignalInput["upi"];
  gst: GSTSignal;
  rent: BorrowerSignalInput["rent"];
  utilities: BorrowerSignalInput["utilities"];
  mobile: BorrowerSignalInput["mobile"];
  employment: BorrowerSignalInput["employment"];
}

const initialFormState: IntakeFormState = {
  borrower_name: "",
  notes: "",
  existing_emi_on_time_ratio: 0.95,
  upi: {
    transaction_frequency_per_month: 80,
    average_transaction_value_inr: 850,
    merchant_diversity_score: 0.65,
    regularity_score: 0.72,
    months_of_history: 12,
    monthly_volume_trend_pct: 5
  },
  gst: {
    filing_frequency: "not_applicable",
    filing_consistency_score: 0,
    missed_filings_last_12m: 0,
    revenue_trend_pct: 0,
    is_applicable: false
  },
  rent: {
    rent_amount_inr: 12000,
    on_time_payment_ratio: 0.9,
    late_payments_last_24m: 1,
    tenancy_months: 24,
    longest_gap_months: 0
  },
  utilities: {
    electricity_on_time_ratio: 0.92,
    water_on_time_ratio: 0.9,
    average_monthly_total_inr: 2800,
    payment_months_observed: 18
  },
  mobile: {
    recharge_frequency_per_month: 1.2,
    average_recharge_value_inr: 399,
    consistency_score: 0.78,
    finance_app_usage_score: 0.71,
    risky_app_usage_score: 0.15,
    monthly_data_usage_gb: 20
  },
  employment: {
    employment_type: "self_employed",
    monthly_income_inr: 42000,
    income_stability_score: 0.74,
    months_in_current_work: 48,
    income_proof_type: "bank_statement"
  }
};

function parseNumber(value: string, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizePayload(form: IntakeFormState): BorrowerSignalInput {
  const declaredAttributes: Record<string, string> = {};
  if (form.notes.trim()) {
    declaredAttributes.assessment_notes = form.notes.trim();
  }

  const gst = form.gst.is_applicable
    ? form.gst
    : {
        filing_frequency: "not_applicable" as const,
        filing_consistency_score: 0,
        missed_filings_last_12m: 0,
        revenue_trend_pct: 0,
        is_applicable: false
      };

  return {
    borrower_name: form.borrower_name.trim(),
    upi: form.upi,
    gst,
    rent: form.rent,
    mobile: form.mobile,
    utilities: form.utilities,
    employment: form.employment,
    existing_emi_on_time_ratio: form.existing_emi_on_time_ratio,
    declared_attributes: declaredAttributes
  };
}

function Section({
  title,
  description,
  children
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="glass-card p-5 sm:p-6">
      <h2 className="headline text-xl font-bold">{title}</h2>
      <p className="mt-1 text-sm muted">{description}</p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{children}</div>
    </section>
  );
}

function FieldLabel({
  label,
  helper,
  children
}: {
  label: string;
  helper?: string;
  children: ReactNode;
}) {
  return (
    <label className="form-label">
      <span>{label}</span>
      {children}
      {helper ? <span className="form-hint">{helper}</span> : null}
    </label>
  );
}

function inputClassName({ disabled = false }: { disabled?: boolean }) {
  return `${disabled ? "form-input opacity-60" : "form-input"}`;
}

export default function IntakePage() {
  const router = useRouter();
  const [form, setForm] = useState<IntakeFormState>(initialFormState);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError(null);

    if (!form.borrower_name.trim()) {
      setSubmitError("Borrower name is required.");
      return;
    }

    setIsSubmitting(true);
    const payload = normalizePayload(form);
    const wasSaved = saveIntakePayload(payload);
    if (!wasSaved) {
      setIsSubmitting(false);
      setSubmitError("Could not save intake data in this browser session. Please retry.");
      return;
    }
    router.push("/ai-processing");
  };

  return (
    <div className="space-y-6">
      <SurfaceCard>
        <span className="eyebrow">Borrower intake</span>
        <h1 className="headline mt-4 text-4xl font-extrabold">Capture alternative-credit signals</h1>
        <p className="mt-2 text-sm muted">
          Collect UPI, GST, repayment, utility, and employment signals before triggering the BharatCredit AI scoring
          pipeline.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <ActionLink href="/landing-page" variant="ghost" className="text-sm">
            Back to home
          </ActionLink>
          <ActionLink href="/persona-selection" variant="secondary" className="text-sm">
            Try persona demo
          </ActionLink>
        </div>
      </SurfaceCard>

      <form className="space-y-5" onSubmit={handleSubmit}>
        <section className="glass-card p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <FieldLabel label="Borrower name">
              <input
                value={form.borrower_name}
                onChange={(event) => {
                  const nextName = event.target.value;
                  setForm((previous) => ({ ...previous, borrower_name: nextName }));
                }}
                className={inputClassName({})}
                placeholder="e.g. Raju Kumar"
                required
              />
            </FieldLabel>
            <FieldLabel label="Existing EMI on-time ratio" helper="0 to 1 scale">
              <input
                type="number"
                step="0.01"
                min={0}
                max={1}
                value={form.existing_emi_on_time_ratio}
                onChange={(event) =>
                  setForm((previous) => ({
                    ...previous,
                    existing_emi_on_time_ratio: parseNumber(event.target.value)
                  }))
                }
                className={inputClassName({})}
                required
              />
            </FieldLabel>
          </div>
          <div className="mt-4">
            <FieldLabel label="Additional notes (optional)">
              <textarea
                value={form.notes}
                onChange={(event) => setForm((previous) => ({ ...previous, notes: event.target.value }))}
                rows={3}
                className={inputClassName({})}
                placeholder="Any manual context you'd like to retain in the report."
              />
            </FieldLabel>
          </div>
        </section>

        <Section title="UPI cashflow signals" description="Digital transaction behavior and consistency.">
          <FieldLabel label="Transactions / month">
            <input
              type="number"
              min={0}
              max={2000}
              value={form.upi.transaction_frequency_per_month}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  upi: {
                    ...previous.upi,
                    transaction_frequency_per_month: parseNumber(event.target.value)
                  }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Average transaction value (₹)">
            <input
              type="number"
              min={0}
              max={1000000}
              value={form.upi.average_transaction_value_inr}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  upi: {
                    ...previous.upi,
                    average_transaction_value_inr: parseNumber(event.target.value)
                  }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Merchant diversity score" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.upi.merchant_diversity_score}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  upi: { ...previous.upi, merchant_diversity_score: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Regularity score" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.upi.regularity_score}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  upi: { ...previous.upi, regularity_score: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Months of UPI history">
            <input
              type="number"
              min={1}
              max={60}
              value={form.upi.months_of_history}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  upi: { ...previous.upi, months_of_history: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Monthly volume trend (%)">
            <input
              type="number"
              min={-100}
              max={300}
              value={form.upi.monthly_volume_trend_pct}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  upi: { ...previous.upi, monthly_volume_trend_pct: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
        </Section>

        <Section title="GST signals" description="Tax behavior for business borrowers.">
          <FieldLabel label="GST applicable">
            <select
              value={form.gst.is_applicable ? "yes" : "no"}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  gst: {
                    ...previous.gst,
                    is_applicable: event.target.value === "yes",
                    filing_frequency: event.target.value === "yes" ? "monthly" : "not_applicable"
                  }
                }))
              }
              className={inputClassName({})}
            >
              <option value="no">No</option>
              <option value="yes">Yes</option>
            </select>
          </FieldLabel>
          <FieldLabel label="Filing frequency">
            <select
              disabled={!form.gst.is_applicable}
              value={form.gst.filing_frequency}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  gst: {
                    ...previous.gst,
                    filing_frequency: event.target.value as GSTSignal["filing_frequency"]
                  }
                }))
              }
              className={inputClassName({ disabled: !form.gst.is_applicable })}
            >
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="not_applicable">Not applicable</option>
            </select>
          </FieldLabel>
          <FieldLabel label="Filing consistency score" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              disabled={!form.gst.is_applicable}
              value={form.gst.filing_consistency_score}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  gst: { ...previous.gst, filing_consistency_score: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({ disabled: !form.gst.is_applicable })}
            />
          </FieldLabel>
          <FieldLabel label="Missed filings (last 12 months)">
            <input
              type="number"
              min={0}
              max={12}
              disabled={!form.gst.is_applicable}
              value={form.gst.missed_filings_last_12m}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  gst: { ...previous.gst, missed_filings_last_12m: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({ disabled: !form.gst.is_applicable })}
            />
          </FieldLabel>
          <FieldLabel label="Revenue trend (%)">
            <input
              type="number"
              min={-100}
              max={300}
              disabled={!form.gst.is_applicable}
              value={form.gst.revenue_trend_pct}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  gst: { ...previous.gst, revenue_trend_pct: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({ disabled: !form.gst.is_applicable })}
            />
          </FieldLabel>
        </Section>

        <Section title="Rental payment signals" description="Housing stability and rent repayment behavior.">
          <FieldLabel label="Monthly rent (₹)">
            <input
              type="number"
              min={0}
              max={500000}
              value={form.rent.rent_amount_inr}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  rent: { ...previous.rent, rent_amount_inr: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="On-time payment ratio" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.rent.on_time_payment_ratio}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  rent: { ...previous.rent, on_time_payment_ratio: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Late payments (last 24 months)">
            <input
              type="number"
              min={0}
              max={24}
              value={form.rent.late_payments_last_24m}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  rent: { ...previous.rent, late_payments_last_24m: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Tenancy months">
            <input
              type="number"
              min={1}
              max={600}
              value={form.rent.tenancy_months}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  rent: { ...previous.rent, tenancy_months: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Longest payment gap (months)">
            <input
              type="number"
              min={0}
              max={36}
              value={form.rent.longest_gap_months}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  rent: { ...previous.rent, longest_gap_months: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
        </Section>

        <Section title="Utility payment signals" description="Electricity and water discipline over time.">
          <FieldLabel label="Electricity on-time ratio" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.utilities.electricity_on_time_ratio}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  utilities: {
                    ...previous.utilities,
                    electricity_on_time_ratio: parseNumber(event.target.value)
                  }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Water on-time ratio" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.utilities.water_on_time_ratio}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  utilities: { ...previous.utilities, water_on_time_ratio: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Average monthly utility total (₹)">
            <input
              type="number"
              min={0}
              max={200000}
              value={form.utilities.average_monthly_total_inr}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  utilities: {
                    ...previous.utilities,
                    average_monthly_total_inr: parseNumber(event.target.value)
                  }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Observed months">
            <input
              type="number"
              min={1}
              max={120}
              value={form.utilities.payment_months_observed}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  utilities: {
                    ...previous.utilities,
                    payment_months_observed: parseNumber(event.target.value)
                  }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
        </Section>

        <Section title="Mobile behavior signals" description="Recharge habits and app usage confidence signals.">
          <FieldLabel label="Recharge frequency / month">
            <input
              type="number"
              step="0.1"
              min={0}
              max={30}
              value={form.mobile.recharge_frequency_per_month}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  mobile: { ...previous.mobile, recharge_frequency_per_month: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Average recharge value (₹)">
            <input
              type="number"
              min={0}
              max={10000}
              value={form.mobile.average_recharge_value_inr}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  mobile: { ...previous.mobile, average_recharge_value_inr: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Recharge consistency score" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.mobile.consistency_score}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  mobile: { ...previous.mobile, consistency_score: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Finance app usage score" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.mobile.finance_app_usage_score}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  mobile: { ...previous.mobile, finance_app_usage_score: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Risky app usage score" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.mobile.risky_app_usage_score}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  mobile: { ...previous.mobile, risky_app_usage_score: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Monthly data usage (GB)">
            <input
              type="number"
              min={0}
              max={500}
              value={form.mobile.monthly_data_usage_gb}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  mobile: { ...previous.mobile, monthly_data_usage_gb: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
        </Section>

        <Section title="Employment and income signals" description="Income strength, continuity, and documentation quality.">
          <FieldLabel label="Employment type">
            <select
              value={form.employment.employment_type}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  employment: {
                    ...previous.employment,
                    employment_type: event.target.value as BorrowerSignalInput["employment"]["employment_type"]
                  }
                }))
              }
              className={inputClassName({})}
            >
              <option value="salaried">Salaried</option>
              <option value="freelance">Freelance</option>
              <option value="self_employed">Self-employed</option>
            </select>
          </FieldLabel>
          <FieldLabel label="Monthly income (₹)">
            <input
              type="number"
              min={0}
              max={5000000}
              value={form.employment.monthly_income_inr}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  employment: { ...previous.employment, monthly_income_inr: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Income stability score" helper="0 to 1 scale">
            <input
              type="number"
              step="0.01"
              min={0}
              max={1}
              value={form.employment.income_stability_score}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  employment: { ...previous.employment, income_stability_score: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Months in current work">
            <input
              type="number"
              min={0}
              max={480}
              value={form.employment.months_in_current_work}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  employment: { ...previous.employment, months_in_current_work: parseNumber(event.target.value) }
                }))
              }
              className={inputClassName({})}
            />
          </FieldLabel>
          <FieldLabel label="Income proof type">
            <select
              value={form.employment.income_proof_type}
              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,
                  employment: {
                    ...previous.employment,
                    income_proof_type: event.target
                      .value as BorrowerSignalInput["employment"]["income_proof_type"]
                  }
                }))
              }
              className={inputClassName({})}
            >
              <option value="salary_slip">Salary slip</option>
              <option value="invoice">Invoice</option>
              <option value="bank_statement">Bank statement</option>
              <option value="self_declared">Self-declared</option>
            </select>
          </FieldLabel>
        </Section>

        {submitError ? (
          <p className="rounded-xl border border-red-400/40 bg-red-500/12 px-3 py-2 text-sm text-red-200">
            {submitError}
          </p>
        ) : null}

        <RbiNotice
          title="RBI & retention notice"
          disclaimer="Submitted inputs are decision-support data and must be used with full KYC, lender underwriting, and RBI digital lending checks."
          retention="Data retention: intake payloads and generated scores may be retained for up to 30 days for audit, grievance handling, and model monitoring."
        />

        <div className="sticky bottom-0 rounded-xl border border-slate-700/45 bg-slate-950/90 p-4 shadow-lg backdrop-blur">
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full text-sm disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Submitting..." : "Submit intake and start scoring"}
          </button>
        </div>
      </form>
    </div>
  );
}

