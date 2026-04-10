import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <SurfaceCard className="overflow-hidden">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-5">
            <span className="eyebrow">Luminal credit engine</span>
            <h1 className="headline text-4xl font-extrabold leading-tight sm:text-5xl">
              Unlock trust for India&apos;s <span className="display-gradient">credit-invisible borrowers</span>
            </h1>
            <p className="max-w-2xl text-base leading-relaxed muted">
              BharatCredit translates transaction behavior, repayment discipline, and compliance patterns into a fast
              lending decision layer with offline continuity when APIs are unavailable.
            </p>
            <div className="flex flex-wrap gap-3">
              <ActionLink href="/intake">Start borrower intake</ActionLink>
              <ActionLink href="/persona-selection" variant="secondary">
                Explore personas
              </ActionLink>
              <ActionLink href="/ai-processing?persona=raju&source=marketing" variant="ghost">
                Live demo run
              </ActionLink>
            </div>
          </div>
          <SurfaceTile className="self-start">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] muted">Signal confidence</p>
            <p className="headline mt-2 text-5xl font-extrabold display-gradient">782</p>
            <p className="mt-2 text-sm muted">Reference score from multi-agent cashflow + compliance synthesis</p>
            <div className="mt-6 space-y-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="muted">Processing latency</span>
                <span className="font-semibold text-emerald-300">&lt; 1.2s</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="muted">Fallback continuity</span>
                <span className="font-semibold text-primary">Enabled</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="muted">Coverage</span>
                <span className="font-semibold text-secondary">UPI + GST + utilities</span>
              </div>
            </div>
          </SurfaceTile>
        </div>
      </SurfaceCard>

      <section className="grid gap-4 sm:grid-cols-3">
        <SurfaceTile>
          <p className="headline text-3xl font-bold text-primary">3x</p>
          <p className="mt-2 text-sm muted">Faster early-stage underwriting for thin-file applicants.</p>
        </SurfaceTile>
        <SurfaceTile>
          <p className="headline text-3xl font-bold text-secondary">Broader</p>
          <p className="mt-2 text-sm muted">Coverage for freelancers, merchants, and micro-entrepreneurs.</p>
        </SurfaceTile>
        <SurfaceTile>
          <p className="headline text-3xl font-bold text-emerald-300">Actionable</p>
          <p className="mt-2 text-sm muted">Agent-level rationale built for responsible lending operations.</p>
        </SurfaceTile>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <SurfaceTile>
          <p className="headline text-xl font-bold">Try advanced journeys</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <ActionLink href="/what-if-analysis" variant="secondary" className="text-sm">
              What-if simulator
            </ActionLink>
            <ActionLink href="/loan-marketplace" variant="ghost" className="text-sm">
              Loan marketplace
            </ActionLink>
          </div>
        </SurfaceTile>
        <SurfaceTile>
          <p className="headline text-xl font-bold">Access & onboarding</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <ActionLink href="/login" variant="ghost" className="text-sm">
              Login
            </ActionLink>
            <ActionLink href="/register" variant="secondary" className="text-sm">
              Register
            </ActionLink>
          </div>
        </SurfaceTile>
      </section>

      <RbiNotice
        disclaimer="BharatCredit outputs are decision-support insights and must be combined with full lender underwriting under prevailing RBI digital lending guidance."
        retention="Data retention: demo and assessment inputs may be retained for up to 30 days for audits, grievance resolution, and model monitoring."
      />
    </div>
  );
}
