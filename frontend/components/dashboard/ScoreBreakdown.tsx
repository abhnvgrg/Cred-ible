import { SurfaceTile } from "@/components/ui/primitives";
import type { ScoreResponse } from "@/lib/scoring";

export function ScoreBreakdown({ response }: { response: ScoreResponse }) {
  return (
    <div className="flex flex-col gap-6 h-full">
      {/* Executive Summary */}
      <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl relative overflow-hidden flex-1 p-6">
        <div className="absolute left-0 top-6 bottom-6 w-1 bg-indigo-400/80 rounded-r-lg" />
        <h2 className="font-bold text-xl mb-3 text-white pl-3">Executive Summary</h2>
        <p className="text-sm text-slate-400 pl-3 leading-relaxed">
          {response.explanation || "This borrower demonstrates strong financial stability characterized by high non-traditional data correlation. While traditional credit depth is moderate, active cash flow through UPI and consistent utility settlements provide a high-confidence lending profile."}
        </p>
      </SurfaceTile>

      {/* Data Composition */}
      <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl flex-1 p-6">
        <div className="flex items-start justify-between mb-1">
          <h2 className="font-bold text-xl text-white">Data Composition</h2>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-slate-500"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
        </div>
        <p className="text-xs text-slate-500 mb-6">Weightage distribution for total score calculation</p>
        
        <div className="space-y-5">
          <div className="space-y-2">
            <div className="flex justify-between text-sm font-semibold">
              <span className="text-slate-200">UPI Transactions</span>
              <span className="text-indigo-400">40%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-400 rounded-full" style={{ width: '40%' }} />
            </div>
          </div>
          
          <div className="space-y-2">
            <div className="flex justify-between text-sm font-semibold">
              <span className="text-slate-200">GST Filings</span>
              <span className="text-purple-400">25%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-purple-400 rounded-full" style={{ width: '25%' }} />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm font-semibold">
              <span className="text-slate-200">Rent Payments</span>
              <span className="text-emerald-400">20%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-400 rounded-full" style={{ width: '20%' }} />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm font-semibold">
              <span className="text-slate-200">Utility Bills</span>
              <span className="text-blue-400">15%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-blue-400 rounded-full" style={{ width: '15%' }} />
            </div>
          </div>
        </div>
      </SurfaceTile>
    </div>
  );
}
