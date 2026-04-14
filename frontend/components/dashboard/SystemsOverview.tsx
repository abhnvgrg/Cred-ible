import { ActionLink, SurfaceTile } from "@/components/ui/primitives";

export function SystemsOverview() {
  return (
    <div className="w-full max-w-[1400px] mx-auto text-slate-200 mb-12">
        <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-white mb-2">Systems Overview</h1>
            <p className="text-slate-400">Monitor your agentic credit assessment infrastructure.</p>
          </div>
          <div className="flex items-center gap-3">
             <ActionLink href="/intake" className="text-sm bg-indigo-500 hover:bg-indigo-400 text-white border-0">
               New Borrower Intake
             </ActionLink>
             <ActionLink href="/persona-selection" variant="secondary" className="text-sm border-indigo-500/30 text-indigo-300">
               Test Personas
             </ActionLink>
          </div>
        </div>

        {/* Global Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 p-6 rounded-2xl relative overflow-hidden shadow-sm">
            <p className="text-sm text-slate-400 font-medium mb-1">Assessments Today</p>
            <p className="text-3xl font-bold text-white">1,492</p>
            <p className="text-xs text-emerald-400 mt-2 font-medium">+12.4% vs yesterday</p>
          </SurfaceTile>
          
          <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 p-6 rounded-2xl relative overflow-hidden shadow-sm">
            <p className="text-sm text-slate-400 font-medium mb-1">Avg. Logic Score</p>
            <p className="text-3xl font-bold text-purple-400">704</p>
            <p className="text-xs text-emerald-400 mt-2 font-medium">+14 pts this week</p>
          </SurfaceTile>

          <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 p-6 rounded-2xl relative overflow-hidden shadow-sm">
            <p className="text-sm text-slate-400 font-medium mb-1">Approval Volume</p>
            <p className="text-3xl font-bold text-white">₹4.2Cr</p>
            <p className="text-xs text-emerald-400 mt-2 font-medium">Within risk tolerance</p>
          </SurfaceTile>

          <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 p-6 rounded-2xl relative overflow-hidden shadow-sm">
            <p className="text-sm text-slate-400 font-medium mb-1">Processing Latency</p>
            <p className="text-3xl font-bold text-white">840ms</p>
            <p className="text-xs text-emerald-400 mt-2 font-medium">99.9% Uptime across agents</p>
          </SurfaceTile>
        </div>

        {/* Middle Section: Chart and System Events */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <SurfaceTile className="lg:col-span-2 bg-slate-900/50 border border-slate-800/80 p-6 rounded-2xl">
            <h3 className="font-bold text-white mb-6">Assessment Volume (Last 7 Days)</h3>
            <div className="w-full h-64 flex items-end justify-between gap-2 border-b border-l border-slate-800 p-4">
              {/* Mock Bar Chart */}
              {Array.from({length: 14}).map((_, i) => (
                <div key={i} className="w-full flex justify-center group relative h-full items-end">
                    <div className="w-full max-w-[32px] bg-indigo-500/20 hover:bg-indigo-500/50 rounded-t-sm transition-all" style={{ height: (30 + (i % 5) * 10 + Math.random() * 20) + "%" }}>
                       <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 bg-slate-800 text-xs px-2 py-1 rounded transition-opacity pointer-events-none">
                         {Math.floor(200 + Math.random() * 400)}
                       </div>
                    </div>
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-4 text-xs font-mono text-slate-500">
               <span>Mon</span>
               <span>Sun</span>
            </div>
          </SurfaceTile>

          <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 p-6 rounded-2xl">
            <h3 className="font-bold text-white mb-6">System Health</h3>
            <div className="space-y-4">
               <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/30 border border-slate-700/30">
                 <div className="flex gap-3 items-center">
                   <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                   <span className="text-sm font-medium text-slate-300">UPI Sync Agent</span>
                 </div>
                 <span className="text-xs text-emerald-400">Operational</span>
               </div>
               <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/30 border border-slate-700/30">
                 <div className="flex gap-3 items-center">
                   <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                   <span className="text-sm font-medium text-slate-300">GST Intelligence</span>
                 </div>
                 <span className="text-xs text-emerald-400">Operational</span>
               </div>
               <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/30 border border-slate-700/30">
                 <div className="flex gap-3 items-center">
                   <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                   <span className="text-sm font-medium text-slate-300">Utility Analysis</span>
                 </div>
                 <span className="text-xs text-emerald-400">Operational</span>
               </div>
               <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/30 border border-slate-700/30">
                 <div className="flex gap-3 items-center">
                   <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                   <span className="text-sm font-medium text-slate-300">RBI Compliance Filter</span>
                 </div>
                 <span className="text-xs text-amber-400">High Latency</span>
               </div>
            </div>
            
            <div className="mt-8 p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
               <p className="text-xs text-indigo-300 mb-2 font-bold uppercase tracking-wider">Ready for Assessment</p>
               <p className="text-sm text-slate-300 mb-4">No borrower context is loaded. Jumpstart the engine by initiating a new flow.</p>
               <div className="flex">
                 <ActionLink href="/intake" className="text-xs w-full justify-center bg-indigo-500 text-white">Start Assessment</ActionLink>
               </div>
            </div>
          </SurfaceTile>
        </div>
      </div>
  );
}
