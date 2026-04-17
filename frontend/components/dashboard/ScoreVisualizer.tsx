import { SurfaceTile } from "@/components/ui/primitives";
import type { ScoreResponse } from "@/lib/scoring";

export function ScoreVisualizer({ response }: { response: ScoreResponse }) {
  return (
    <SurfaceTile className="flex flex-col items-center justify-center py-14 bg-slate-900/50 border border-slate-800/80 rounded-2xl relative shadow-sm">
      <div className="relative w-64 h-64 mx-auto mb-8">
        <svg className="w-full h-full transform -rotate-90 scale-x-[-1]" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="44" fill="transparent" stroke="rgba(255,255,255,0.03)" strokeWidth="8"/>
          <circle cx="50" cy="50" r="44" fill="transparent" stroke="#a855f7" strokeWidth="8" strokeDasharray="276" strokeDashoffset="60" strokeLinecap="round"/>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-7xl font-extrabold text-white tracking-tight">{response.final_score}</span>
          <span className="text-[11px] font-semibold tracking-widest text-slate-400 uppercase mt-1">Out of 900</span>
        </div>
      </div>
      
      <div className="bg-red-500/10 border border-red-500/20 px-4 py-1.5 rounded-full flex items-center gap-2 mb-4">
        <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
        <span className="text-xs font-bold text-red-400 uppercase tracking-wider">Risk Level: Medium</span>
      </div>
      
      <p className="text-sm font-medium text-slate-300">
        Confidence Score: <span className="text-indigo-400">{response.confidence === 'high' ? '94%' : response.confidence === 'medium' ? '70%' : '45%'}</span>
      </p>
    </SurfaceTile>
  );
}
