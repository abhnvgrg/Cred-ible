import { SurfaceTile } from "@/components/ui/primitives";
import type { ScoreResponse } from "@/lib/scoring";

export function ScoreInsights({ response }: { response: ScoreResponse }) {
  return (
    <>
      {/* Positive Factors */}
      <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-md bg-emerald-500/10 flex items-center justify-center text-emerald-400">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="m3 17 6-6 4 4 8-8"/><path d="M17 7h4v4"/></svg>
          </div>
          <h3 className="font-bold text-white">Positive Factors</h3>
        </div>
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 border-l-2 border-l-emerald-500">
            <p className="text-sm font-semibold text-white">Consistent monthly income</p>
            <p className="text-xs text-slate-400 mt-1">Verified via multi-source bank statement analysis.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 border-l-2 border-l-emerald-500">
            <p className="text-sm font-semibold text-white">Zero late rent payments</p>
            <p className="text-xs text-slate-400 mt-1">12-month track record with verified digital receipts.</p>
          </div>
        </div>
      </SurfaceTile>

      {/* Risk Factors */}
      <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-md bg-red-500/10 flex items-center justify-center text-red-500">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>
          </div>
          <h3 className="font-bold text-white">Risk Factors</h3>
        </div>
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 border-l-2 border-l-red-500">
            <p className="text-sm font-semibold text-white">Irregular GST filings</p>
            <p className="text-xs text-slate-400 mt-1">2 filing delays detected in the last 6 months.</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-700/50 border-l-2 border-l-red-500">
            <p className="text-sm font-semibold text-white">High credit utilization</p>
            <p className="text-xs text-slate-400 mt-1">Current usage stands at 68% of available limits.</p>
          </div>
        </div>
      </SurfaceTile>

      {/* Recommended Loan */}
      <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6 flex flex-col">
        <h3 className="font-bold text-white mb-2">Recommended Loan</h3>
        <p className="text-4xl font-extrabold text-purple-400 mb-6">{response.recommended_loan_limit}</p>
        
        <div className="bg-black/30 p-4 rounded-xl mb-6 flex-1">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">AI Reasoning</p>
          <p className="text-sm text-slate-300 font-medium leading-relaxed">
            Optimal risk-to-yield ratio based on current UPI inflow velocity.
          </p>
        </div>

        <button className="w-full py-3 rounded-lg bg-indigo-400 text-white font-bold text-sm hover:bg-indigo-500 transition-colors">
          Apply Now
        </button>
      </SurfaceTile>
    </>
  );
}
