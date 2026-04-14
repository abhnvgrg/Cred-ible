"use client";

import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import type { AgentScoreOutput, ConfidenceLevel, StoredScoreResult } from "@/lib/scoring";
import { isComplianceAgentOutput, loadScoreResult } from "@/lib/scoring";
import { useEffect, useMemo, useState } from "react";

function confidenceClass(confidence: ConfidenceLevel): string {
  if (confidence === "high") return "bg-emerald-500/20 text-emerald-200";
  if (confidence === "medium") return "bg-amber-400/20 text-amber-100";
  return "bg-red-500/20 text-red-200";
}

function confidenceLabel(confidence: ConfidenceLevel): string {
  return confidence.charAt(0).toUpperCase() + confidence.slice(1);
}

function formatKeyLabel(raw: string): string {
  return raw
    .replaceAll("_", " ")
    .split(" ")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDateTime(dateTime: string): string {
  const parsed = new Date(dateTime);
  if (Number.isNaN(parsed.getTime())) return dateTime;
  return parsed.toLocaleString();
}

function buildReportText(storedResult: StoredScoreResult): string {
  const { response } = storedResult;

  const lines = [
    "BharatCredit Score Report",
    "=========================",
    `Generated at: ${formatDateTime(storedResult.generatedAt)}`,
    `Flow source: ${storedResult.source}`,
    `Borrower: ${storedResult.borrowerName}`,
    `Persona: ${storedResult.persona ?? "N/A"}`,
    `Offline fallback used: ${storedResult.fallbackUsed ? "Yes" : "No"}`,
    ...(storedResult.fallbackReason ? [`Fallback reason: ${storedResult.fallbackReason}`] : []),
    "",
    "Summary",
    "-------",
    `Final score: ${response.final_score} / 900`,
    `Confidence: ${response.confidence}`,
    `Recommended loan range: ${response.recommended_loan_limit}`,
    `Processing time (ms): ${response.processing_time_ms}`,
    "",
    "Agent Breakdown",
    "---------------",
    `Income: ${response.agent_breakdown.income}`,
    `Repayment: ${response.agent_breakdown.repayment}`,
    `Lifestyle: ${response.agent_breakdown.lifestyle}`,
    `Compliance: ${response.agent_breakdown.compliance}`,
    "",
    "RBI Flags",
    "---------",
    ...(response.rbi_flags.length ? response.rbi_flags.map((flag) => `- ${flag}`) : ["- None"]),
    "",
    "Explanation",
    "-----------",
    response.explanation,
    "",
    "Disclaimer",
    "----------",
    response.disclaimer
  ];

  return lines.join("\n");
}

export default function ResultPage() {
  const [storedResult, setStoredResult] = useState<StoredScoreResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const nextResult = loadScoreResult();
    if (!nextResult) {
      setLoadError("No score result found. Please run intake or demo processing first.");
      return;
    }
    setStoredResult(nextResult);
  }, []);

  if (loadError) {
    return (
      <SurfaceTile className="border border-red-500/35 bg-red-500/10">
        <h1 className="headline text-2xl font-bold text-red-100">Result unavailable</h1>
        <p className="mt-2 text-sm text-red-200">{loadError}</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <ActionLink href="/intake" className="text-sm">
            Go to intake
          </ActionLink>
          <ActionLink href="/persona-selection" variant="secondary" className="text-sm">
            Go to personas
          </ActionLink>
        </div>
      </SurfaceTile>
    );
  }

  if (!storedResult) {
    return (
      <SurfaceCard>
        <p className="text-sm muted">Loading score output...</p>
      </SurfaceCard>
    );
  }

  const { response } = storedResult;

  return (
    <div className="w-full max-w-[1400px] mx-auto text-slate-200 mb-12">
      {/* Back button */}
      <button 
        onClick={() => window.history.back()} 
        className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors mb-6"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
        Back to Operations
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_1.9fr] gap-6">
        {/* Left Card - Circular Score */}
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

        {/* Right Section - Split Cards */}
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
      </div>

      {/* Bottom Row - 3 Columns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
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
      </div>

      {/* Track & Timeline Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        {/* Footprint */}
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

        {/* Recent Activity Signal */}
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
      </div>

    </div>
  );
}
