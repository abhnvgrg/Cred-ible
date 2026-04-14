import { SurfaceTile } from "@/components/ui/primitives";

export function RecentActivity() {
  return (
    <SurfaceTile className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-bold text-white">Recent Activity Signal</h3>
        <button className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors">View All</button>
      </div>
      
      <div className="space-y-3">
        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/40">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center text-indigo-300">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m13 2-2 2.5h3L11 22l2-2.5H10l3-17z"/></svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Electricity Bill Paid</p>
              <p className="text-xs text-slate-400">Verified via Bharat BillPay</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm font-bold text-emerald-400">+ 12 pts</p>
            <p className="text-xs text-slate-500">Yesterday</p>
          </div>
        </div>

        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/40">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center text-purple-400">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/></svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-white">New Credit Inquiry</p>
              <p className="text-xs text-slate-400">HDFC Bank Personal Loan</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm font-bold text-red-500">- 4 pts</p>
            <p className="text-xs text-slate-500">3 days ago</p>
          </div>
        </div>

        <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/40">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center text-emerald-400">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/></svg>
            </div>
            <div>
              <p className="text-sm font-semibold text-white">Rent Transfer Confirmed</p>
              <p className="text-xs text-slate-400">M.K. Properties (Verified)</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm font-bold text-emerald-400">+ 18 pts</p>
            <p className="text-xs text-slate-500">Oct 1, 2024</p>
          </div>
        </div>
      </div>
    </SurfaceTile>
  );
}
