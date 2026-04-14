import { SurfaceTile } from "@/components/ui/primitives";

export function FinancialFootprint() {
  return (
    <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6">
      <h3 className="font-bold text-white mb-6">Financial Footprint</h3>
      <div className="w-full h-[250px] rounded-xl bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-teal-900/40 via-slate-900 to-black border border-slate-800 relative flex items-center justify-center overflow-hidden">
        {/* Mocked UI for Dashboard view */}
        <div className="absolute inset-0 opacity-30 flex gap-1 p-4">
           {Array.from({length: 40}).map((_, i) => (
             <div key={i} className="flex-1 bg-teal-500/20 mt-auto" style={{ height: (20 + Math.random() * 80) + "%" }} />
           ))}
        </div>
        <div className="absolute bottom-4 left-4 bg-teal-500/20 text-teal-400 px-2 py-1 text-[10px] font-mono tracking-widest border border-teal-500/30 rounded">
          LIVE_TRACKING_ON
        </div>
        <div className="w-48 h-24 border border-teal-500/40 bg-black/50 rounded-lg flex items-center p-3 gap-3 mr-24">
          <div className="w-12 h-12 rounded-full border-[3px] border-teal-500/40 border-t-teal-400 flex items-center justify-center text-xs text-teal-300 font-bold">96%</div>
          <div className="flex-1 space-y-1">
            <div className="h-1 bg-teal-500/20 rounded w-full"><div className="h-1 bg-teal-400 rounded w-3/4"></div></div>
            <div className="h-1 bg-teal-500/20 rounded w-full"><div className="h-1 bg-teal-400 rounded w-1/2"></div></div>
            <div className="h-1 bg-teal-500/20 rounded w-full"><div className="h-1 bg-teal-400 rounded w-5/6"></div></div>
          </div>
        </div>
      </div>
    </SurfaceTile>
  );
}
