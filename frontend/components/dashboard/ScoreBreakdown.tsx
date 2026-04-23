import { SurfaceTile } from "@/components/ui/primitives";
import type { ScoreResponse } from "@/lib/scoring";

const FALLBACK_WEIGHTS = {
  income: 0.4,
  repayment: 0.4,
  lifestyle: 0.2
};

export function ScoreBreakdown({ response }: { response: ScoreResponse }) {
  const weights = {
    income: response.component_weights?.income ?? FALLBACK_WEIGHTS.income,
    repayment: response.component_weights?.repayment ?? FALLBACK_WEIGHTS.repayment,
    lifestyle: response.component_weights?.lifestyle ?? FALLBACK_WEIGHTS.lifestyle
  };

  const contributions = {
    income: response.component_contributions?.income ?? response.agent_breakdown.income * weights.income,
    repayment: response.component_contributions?.repayment ?? response.agent_breakdown.repayment * weights.repayment,
    lifestyle: response.component_contributions?.lifestyle ?? response.agent_breakdown.lifestyle * weights.lifestyle
  };

  const rows = [
    {
      label: "Income agent",
      score: response.agent_breakdown.income,
      weightPct: Math.round(weights.income * 100),
      contribution: contributions.income,
      barClass: "bg-indigo-400",
      textClass: "text-indigo-400"
    },
    {
      label: "Repayment agent",
      score: response.agent_breakdown.repayment,
      weightPct: Math.round(weights.repayment * 100),
      contribution: contributions.repayment,
      barClass: "bg-emerald-400",
      textClass: "text-emerald-400"
    },
    {
      label: "Lifestyle agent",
      score: response.agent_breakdown.lifestyle,
      weightPct: Math.round(weights.lifestyle * 100),
      contribution: contributions.lifestyle,
      barClass: "bg-purple-400",
      textClass: "text-purple-400"
    }
  ];

  return (
    <div className="flex flex-col gap-6 h-full">
      <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl relative overflow-hidden flex-1 p-6">
        <div className="absolute left-0 top-6 bottom-6 w-1 bg-indigo-400/80 rounded-r-lg" />
        <h2 className="font-bold text-xl mb-3 text-white pl-3">Executive Summary</h2>
        <p className="text-sm text-slate-400 pl-3 leading-relaxed">{response.explanation}</p>
      </SurfaceTile>

      <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl flex-1 p-6">
        <div className="flex items-start justify-between mb-1">
          <h2 className="font-bold text-xl text-white">Data Composition</h2>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-slate-500"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4" />
            <path d="M12 8h.01" />
          </svg>
        </div>
        <p className="text-xs text-slate-500 mb-6">Live backend-calculated component scores and weighted contributions</p>

        <div className="space-y-5">
          {rows.map((row) => (
            <div key={row.label} className="space-y-2">
              <div className="flex justify-between text-sm font-semibold">
                <span className="text-slate-200">{row.label}</span>
                <span className={row.textClass}>
                  {row.score}/100 • {row.weightPct}% weight • {row.contribution.toFixed(1)} pts
                </span>
              </div>
              <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                <div className={`h-full ${row.barClass} rounded-full`} style={{ width: `${row.score}%` }} />
              </div>
            </div>
          ))}
        </div>
      </SurfaceTile>
    </div>
  );
}
