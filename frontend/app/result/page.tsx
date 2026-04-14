"use client";

import { SurfaceCard } from "@/components/ui/primitives";
import type { StoredScoreResult } from "@/lib/scoring";
import { loadScoreResult } from "@/lib/scoring";
import { useEffect, useState } from "react";

// Dashboard Components
import { SystemsOverview } from "@/components/dashboard/SystemsOverview";
import { ScoreVisualizer } from "@/components/dashboard/ScoreVisualizer";
import { ScoreBreakdown } from "@/components/dashboard/ScoreBreakdown";
import { ScoreInsights } from "@/components/dashboard/ScoreInsights";
import { FinancialFootprint } from "@/components/dashboard/FinancialFootprint";
import { RecentActivity } from "@/components/dashboard/RecentActivity";

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
    return <SystemsOverview />;
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
        <ScoreVisualizer response={response} />
        <ScoreBreakdown response={response} />
      </div>

      {/* Bottom Row - 3 Columns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        <ScoreInsights response={response} />
      </div>

      {/* Track & Timeline Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        <FinancialFootprint />
        <RecentActivity />
      </div>
    </div>
  );
}
