"use client";

import { motion, type Variants } from "framer-motion";
import { Activity, Play, Settings, Database, Server, Zap, Compass, Calculator, Store, Sparkles } from "lucide-react";
import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.12 }
  }
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 30, filter: "blur(8px)" },
  visible: { opacity: 1, y: 0, filter: "blur(0px)", transition: { type: "spring" as const, stiffness: 300, damping: 28 } }
};

export default function HomePage() {
  return (
    <motion.div
      className="space-y-10 pb-10"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Hero Section */}
      <motion.div variants={itemVariants} className="text-center max-w-4xl mx-auto pt-8 sm:pt-14 pb-4">
        <div className="flex justify-center mb-8">
          <span className="eyebrow">
            <Sparkles className="w-3.5 h-3.5" /> Introducing Cred-ible
          </span>
        </div>
        <h1 className="headline text-5xl font-extrabold leading-[1.05] sm:text-6xl md:text-[5rem] mb-6 tracking-tighter">
          Unlock trust for India&apos;s <br className="hidden sm:block" />
          <span className="display-gradient">credit-invisible borrowers.</span>
        </h1>
        <p className="max-w-2xl mx-auto text-lg leading-relaxed text-slate-400 mb-10">
          Cred-ible translates transaction behavior, repayment discipline, and compliance patterns into a fast
          lending decision layer with seamless offline continuity.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <ActionLink href="/intake"><Zap className="w-4 h-4" /> Start borrower intake</ActionLink>
          <ActionLink href="/persona-selection" variant="secondary">
            <Compass className="w-4 h-4 text-slate-400" /> Explore personas
          </ActionLink>
        </div>
      </motion.div>

      {/* Showcase Card */}
      <motion.div variants={itemVariants} className="max-w-5xl mx-auto relative z-10">
        <SurfaceCard className="p-1 md:p-1.5 bg-gradient-to-b from-white/[0.08] to-transparent shadow-[0_40px_80px_rgba(0,0,0,0.5)]">
          <div className="rounded-[28px] overflow-hidden bg-surface-low border border-white/[0.04] p-8 md:p-12 relative flex flex-col md:flex-row items-center gap-12 shadow-[inset_0_1px_0_rgba(255,255,255,0.02)]">

            {/* Left Decor / Demo */}
            <div className="flex-1 w-full max-w-sm mx-auto">
              <SurfaceTile className="relative ring-1 ring-white/[0.02]">
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] border border-indigo-500/20">
                      <Activity className="w-5 h-5" />
                    </div>
                    <span className="text-sm font-semibold text-slate-200 tracking-tight">Real-time Analysis</span>
                  </div>
                  <span className="text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2.5 py-1.5 rounded-full border border-emerald-400/20">+24.5% Accuracy</span>
                </div>

                <div className="relative w-48 h-48 sm:w-56 sm:h-56 mx-auto my-6">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="42" fill="transparent" stroke="rgba(255,255,255,0.03)" strokeWidth="6" />
                    <motion.circle
                      cx="50" cy="50" r="42" fill="transparent" stroke="url(#gradient)" strokeWidth="6"
                      strokeDasharray="264"
                      strokeLinecap="round"
                      initial={{ strokeDashoffset: 264 }}
                      animate={{ strokeDashoffset: 56 }}
                      transition={{ duration: 2.5, ease: "easeOut", delay: 0.8 }}
                    />
                    <defs>
                      <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#818cf8" />
                        <stop offset="100%" stopColor="#a78bfa" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <motion.span
                      className="text-6xl font-extrabold text-white tracking-tighter"
                      initial={{ opacity: 0, scale: 0.8, filter: "blur(4px)" }}
                      animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
                      transition={{ delay: 1.2, duration: 0.8 }}
                    >
                      782
                    </motion.span>
                    <span className="text-[10px] font-bold tracking-[0.2em] text-indigo-300 uppercase mt-2">Logic Score</span>
                  </div>
                </div>

                <div className="space-y-4 text-sm border-t border-white/[0.04] pt-6 relative mt-4">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 flex items-center gap-2"><Server className="w-4 h-4" /> Processing latency</span>
                    <span className="font-semibold text-emerald-400">&lt; 1.2s</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 flex items-center gap-2"><Database className="w-4 h-4" /> Coverage</span>
                    <span className="font-semibold text-indigo-300">UPI + GST</span>
                  </div>
                </div>
              </SurfaceTile>
            </div>

            {/* Right text context */}
            <div className="flex-1 space-y-6 text-center md:text-left">
              <h2 className="text-3xl font-extrabold text-white tracking-tight headline">AI-driven cashflow underwriting.</h2>
              <p className="text-slate-400 leading-relaxed text-base">
                Simulate borrower personas securely. Watch as the engine rapidly aggregates
                alternative data to provide high-probability approval logic within milliseconds,
                eliminating the &quot;thin-file&quot; penalty forever.
              </p>
              <div className="pt-4">
                <ActionLink href="/ai-processing?persona=raju&source=marketing" variant="ghost" className="border border-indigo-500/30 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-200">
                  <Play className="w-4 h-4" /> Run simulation demo
                </ActionLink>
              </div>
            </div>

          </div>
        </SurfaceCard>
      </motion.div>

      {/* Features Grid */}
      <motion.section variants={containerVariants} className="grid gap-4 sm:grid-cols-3 max-w-5xl mx-auto pt-6">
        <motion.div variants={itemVariants} className="h-full">
          <SurfaceTile className="h-full group">
            <p className="headline text-4xl font-extrabold text-indigo-300 mb-3 group-hover:scale-105 transition-transform origin-left">3x</p>
            <p className="text-sm muted leading-relaxed">Faster early-stage underwriting for thin-file applicants with no credit history.</p>
          </SurfaceTile>
        </motion.div>
        <motion.div variants={itemVariants} className="h-full">
          <SurfaceTile className="h-full group">
            <p className="headline text-3xl font-extrabold text-violet-300 mb-3 group-hover:scale-105 transition-transform origin-left">Broader</p>
            <p className="text-sm muted leading-relaxed">Coverage for freelancers, local merchants, and micro-entrepreneurs securely.</p>
          </SurfaceTile>
        </motion.div>
        <motion.div variants={itemVariants} className="h-full">
          <SurfaceTile className="h-full group">
            <p className="headline text-3xl font-extrabold text-emerald-300 mb-3 group-hover:scale-105 transition-transform origin-left">Actionable</p>
            <p className="text-sm muted leading-relaxed">Agent-level lending rationale built exclusively for responsible operations.</p>
          </SurfaceTile>
        </motion.div>
      </motion.section>

      {/* Journeys */}
      <motion.section variants={containerVariants} className="grid gap-4 sm:grid-cols-2 max-w-5xl mx-auto pt-4">
        <motion.div variants={itemVariants}>
          <SurfaceTile className="p-8 group">
            <div className="flex items-center justify-between mb-6">
              <p className="headline text-2xl font-bold text-slate-100 flex items-center gap-3">
                <Calculator className="w-6 h-6 text-violet-400 group-hover:scale-110 transition-transform" /> Advanced Journeys
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <ActionLink href="/what-if-analysis" variant="secondary" className="text-sm">
                What-if simulator
              </ActionLink>
              <ActionLink href="/loan-marketplace" variant="ghost" className="text-sm">
                Loan marketplace
              </ActionLink>
            </div>
          </SurfaceTile>
        </motion.div>
        <motion.div variants={itemVariants}>
          <SurfaceTile className="p-8 group">
            <div className="flex items-center justify-between mb-6">
              <p className="headline text-2xl font-bold text-slate-100 flex items-center gap-3">
                <Store className="w-6 h-6 text-indigo-400 group-hover:scale-110 transition-transform" /> Partner Access
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <ActionLink href="/login" variant="secondary" className="text-sm">
                Portal Login
              </ActionLink>
              <ActionLink href="/register" variant="ghost" className="text-sm">
                Register Entity
              </ActionLink>
            </div>
          </SurfaceTile>
        </motion.div>
      </motion.section>

      {/* Footer Notice */}
      <motion.div variants={itemVariants} className="max-w-5xl mx-auto pt-8">
        <RbiNotice
          disclaimer="Cred-ible outputs are decision-support insights and must be combined with full lender underwriting under prevailing RBI digital lending guidance."
          retention="Data retention: demo and assessment inputs may be retained for up to 30 days for audits, grievance resolution, and model monitoring."
        />
      </motion.div>
    </motion.div>
  );
}
