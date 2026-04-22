import { SurfaceTile } from "@/components/ui/primitives";
import type { FraudRiskLevel, ScoreResponse } from "@/lib/scoring";

function deriveRiskLevel(response: ScoreResponse): FraudRiskLevel {
  if (response.risk_level) return response.risk_level;
  if (response.final_score >= 760) return "low";
  if (response.final_score >= 620) return "medium";
  return "high";
}

export function ScoreVisualizer({ response }: { response: ScoreResponse }) {
  const riskLevel = deriveRiskLevel(response);
  const confidencePct = response.confidence === "high" ? 94 : response.confidence === "medium" ? 70 : 45;

  const progressRatio = Math.max(0, Math.min(1, (response.final_score - 300) / 600));
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - progressRatio);

  const riskPillClass =
    riskLevel === "low"
      ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
      : riskLevel === "medium"
        ? "bg-amber-500/10 border-amber-500/20 text-amber-300"
        : "bg-red-500/10 border-red-500/20 text-red-300";

  return (
    <SurfaceTile className="flex flex-col items-center justify-center py-14 bg-slate-900/50 border border-slate-800/80 rounded-2xl relative shadow-sm">
      <div className="relative w-64 h-64 mx-auto mb-8">
        <svg className="w-full h-full transform -rotate-90 scale-x-[-1]" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r={radius} fill="transparent" stroke="rgba(255,255,255,0.03)" strokeWidth="8" />
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="transparent"
            stroke="#a855f7"
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-7xl font-extrabold text-white tracking-tight">{response.final_score}</span>
          <span className="text-[11px] font-semibold tracking-widest text-slate-400 uppercase mt-1">Out of 900</span>
        </div>
      </div>

      <div className={`px-4 py-1.5 rounded-full flex items-center gap-2 mb-4 border ${riskPillClass}`}>
        <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
        <span className="text-xs font-bold uppercase tracking-wider">Risk Level: {riskLevel}</span>
      </div>

      <p className="text-sm font-medium text-slate-300">
        Confidence Score: <span className="text-indigo-400">{confidencePct}%</span>
      </p>
    </SurfaceTile>
  );
}
