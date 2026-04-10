"use client";

import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import { apiFetch } from "@/lib/api";
import { loadScoreResult } from "@/lib/scoring";
import { useEffect, useState } from "react";

interface MarketplaceOffer {
  lender: string;
  product_type: string;
  eligible_amount_inr: number;
  indicative_rate_apr: number;
  tenure_months: number;
  ai_match_pct: number;
  rationale: string;
  requires_additional_docs: boolean;
}

interface MarketplaceResponse {
  score_used: number;
  confidence: "high" | "medium" | "low";
  offers: MarketplaceOffer[];
  disclaimer: string;
}

function formatInr(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(value);
}

export default function MarketplacePage() {
  const [score, setScore] = useState(714);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [data, setData] = useState<MarketplaceResponse | null>(null);

  useEffect(() => {
    const result = loadScoreResult();
    if (result) {
      setScore(result.response.final_score);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await apiFetch<MarketplaceResponse>("/marketplace/offers", {
          query: { score },
          timeoutMs: 12000
        });
        if (!cancelled) {
          setData(response);
        }
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : "Unable to load offers.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [score]);

  const offers = data?.offers ?? [];

  return (
    <div className="space-y-6">
      <SurfaceCard>
        <span className="eyebrow">Loan marketplace</span>
        <h1 className="headline mt-4 text-4xl font-extrabold">Matched lending opportunities</h1>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed muted">
          Offers are ranked by BharatCredit signal confidence and eligibility compatibility across lender partner
          policy profiles.
        </p>
      </SurfaceCard>

      <SurfaceTile className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.14em] muted">Current luminal score</p>
          <p className="headline mt-1 text-4xl font-extrabold display-gradient">{data?.score_used ?? score}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <ActionLink href="/what-if-analysis" variant="secondary" className="text-sm">
            Tune with what-if
          </ActionLink>
          <ActionLink href="/intake" variant="ghost" className="text-sm">
            New borrower intake
          </ActionLink>
        </div>
      </SurfaceTile>

      {isLoading ? <SurfaceCard className="text-sm muted">Loading lender offers...</SurfaceCard> : null}
      {errorMessage ? <SurfaceCard className="text-sm text-red-200">{errorMessage}</SurfaceCard> : null}

      <section className="space-y-4">
        {offers.map((offer) => (
          <SurfaceCard key={offer.lender} as="article" className="py-5">
            <div className="grid gap-4 md:grid-cols-[1.2fr_1fr_1fr_0.8fr_auto] md:items-center">
              <div>
                <p className="headline text-2xl font-bold">{offer.lender}</p>
                <p className="text-sm muted">
                  {offer.product_type}
                  {offer.requires_additional_docs ? " • additional docs may be required" : ""}
                </p>
                <p className="mt-1 text-xs muted">{offer.rationale}</p>
              </div>
              <Metric label="Eligible amount" value={formatInr(offer.eligible_amount_inr)} />
              <Metric label="Indicative rate" value={`${offer.indicative_rate_apr.toFixed(2)}% p.a.`} />
              <Metric label="AI match" value={`${offer.ai_match_pct}%`} valueClassName="text-primary" />
              <ActionLink href="/ai-processing" className="text-sm">
                Apply path
              </ActionLink>
            </div>
          </SurfaceCard>
        ))}
      </section>

      <RbiNotice
        disclaimer={
          data?.disclaimer ??
          "Marketplace suggestions are pre-screened decision-support references and do not constitute sanctioned credit."
        }
        retention="Data retention: offer interaction events may be retained for up to 30 days for audit traceability and model monitoring."
      />
    </div>
  );
}

function Metric({
  label,
  value,
  valueClassName
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.13em] muted">{label}</p>
      <p className={`headline mt-1 text-xl font-bold ${valueClassName ?? ""}`}>{value}</p>
    </div>
  );
}
