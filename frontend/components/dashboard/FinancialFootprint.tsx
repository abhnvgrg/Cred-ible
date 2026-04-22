import { SurfaceTile } from "@/components/ui/primitives";
import type { ScoreResponse } from "@/lib/scoring";

export function FinancialFootprint({ response }: { response: ScoreResponse }) {
  const metrics = [
    { label: "Final score", value: `${response.final_score}/900` },
    { label: "Risk level", value: response.risk_level ?? (response.final_score >= 760 ? "low" : response.final_score >= 620 ? "medium" : "high") },
    { label: "Confidence", value: response.confidence },
    { label: "Processing time", value: `${response.processing_time_ms} ms` },
    { label: "RBI flags", value: String(response.rbi_flags.length) },
    { label: "Compliance", value: response.agent_breakdown.compliance }
  ];

  return (
    <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6">
      <h3 className="font-bold text-white mb-6">Financial Footprint</h3>
      <div className="grid gap-3 sm:grid-cols-2">
        {metrics.map((metric) => (
          <div key={metric.label} className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50">
            <p className="text-xs uppercase tracking-[0.12em] text-slate-400">{metric.label}</p>
            <p className="mt-2 text-lg font-bold text-slate-100">{metric.value}</p>
          </div>
        ))}
      </div>
    </SurfaceTile>
  );
}
