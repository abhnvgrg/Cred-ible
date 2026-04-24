"use client";

import { motion } from "framer-motion";
import { Activity, Play, Settings, Database, Server, Zap, Compass, Calculator, Store, Sparkles } from "lucide-react";
import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
};

export default function HomePage() {
  return (
    <motion.div 
      className="space-y-8"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.div variants={itemVariants}>
        <SurfaceCard className="overflow-hidden">
          <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="space-y-5">
              <span className="eyebrow">
                <Sparkles className="w-3 h-3" /> Cred-ible credit engine
              </span>
              <h1 className="headline text-4xl font-extrabold leading-tight sm:text-5xl">
                Unlock trust for India&apos;s <span className="display-gradient">credit-invisible borrowers</span>
              </h1>
              <p className="max-w-2xl text-base leading-relaxed muted">
                Cred-ible translates transaction behavior, repayment discipline, and compliance patterns into a fast
                lending decision layer with offline continuity when APIs are unavailable.
              </p>
              <div className="flex flex-wrap gap-3">
                <ActionLink href="/intake"><Zap className="w-4 h-4" /> Start borrower intake</ActionLink>
                <ActionLink href="/persona-selection" variant="secondary">
                  <Compass className="w-4 h-4" /> Explore personas
                </ActionLink>
                <ActionLink href="/ai-processing?persona=raju&source=marketing" variant="ghost">
                  <Play className="w-4 h-4" /> Live demo run
                </ActionLink>
              </div>
            </div>
            <SurfaceTile className="self-start">
              {/* Top row with Real-time Analysis and Accuracy */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="flex items-center justify-center w-8 h-8 rounded-md bg-indigo-500/10 text-indigo-400">
                    <Activity className="w-4 h-4" />
                  </div>
                  <span className="text-sm font-semibold text-white">Real-time Analysis</span>
                </div>
                <span className="text-xs font-bold text-emerald-400">+24.5% Accuracy</span>
              </div>

              {/* Circular Progress Bar */}
              <div className="relative w-48 h-48 mx-auto my-8">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="42" fill="transparent" stroke="rgba(255,255,255,0.05)" strokeWidth="8"/>
                  <motion.circle 
                    cx="50" cy="50" r="42" fill="transparent" stroke="#4ade80" strokeWidth="8" 
                    strokeDasharray="264" 
                    strokeLinecap="round"
                    initial={{ strokeDashoffset: 264 }}
                    animate={{ strokeDashoffset: 56 }}
                    transition={{ duration: 2, ease: "easeOut", delay: 0.5 }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center mt-2">
                  <motion.span 
                    className="text-5xl font-bold text-white"
                    initial={{ opacity: 0, scale: 0.5 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 1, type: "spring" }}
                  >
                    782
                  </motion.span>
                  <span className="text-[10px] tracking-widest text-gray-400 uppercase mt-1">Logic Score</span>
                </div>
              </div>

              <p className="text-center text-xs italic text-gray-400 mb-8 px-4">
                &quot;High probability of approval based on cashflow analysis&quot;
              </p>

              <div className="space-y-3 text-sm border-t border-white/5 pt-6">
                <div className="flex items-center justify-between">
                  <span className="muted flex items-center gap-1.5"><Server className="w-3.5 h-3.5" /> Processing latency</span>
                  <span className="font-semibold text-emerald-300">&lt; 1.2s</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="muted flex items-center gap-1.5"><Settings className="w-3.5 h-3.5" /> Fallback continuity</span>
                  <span className="font-semibold text-primary">Enabled</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="muted flex items-center gap-1.5"><Database className="w-3.5 h-3.5" /> Coverage</span>
                  <span className="font-semibold text-secondary">UPI + GST + utilities</span>
                </div>
              </div>
            </SurfaceTile>
          </div>
        </SurfaceCard>
      </motion.div>

      <motion.section variants={containerVariants} className="grid gap-4 sm:grid-cols-3">
        <motion.div variants={itemVariants} className="h-full">
          <SurfaceTile className="h-full">
            <p className="headline text-3xl font-bold text-primary">3x</p>
            <p className="mt-2 text-sm muted">Faster early-stage underwriting for thin-file applicants.</p>
          </SurfaceTile>
        </motion.div>
        <motion.div variants={itemVariants} className="h-full">
          <SurfaceTile className="h-full">
            <p className="headline text-3xl font-bold text-secondary">Broader</p>
            <p className="mt-2 text-sm muted">Coverage for freelancers, merchants, and micro-entrepreneurs.</p>
          </SurfaceTile>
        </motion.div>
        <motion.div variants={itemVariants} className="h-full">
          <SurfaceTile className="h-full">
            <p className="headline text-3xl font-bold text-emerald-300">Actionable</p>
            <p className="mt-2 text-sm muted">Agent-level rationale built for responsible lending operations.</p>
          </SurfaceTile>
        </motion.div>
      </motion.section>

      <motion.section variants={containerVariants} className="grid gap-4 sm:grid-cols-2">
        <motion.div variants={itemVariants}>
          <SurfaceTile>
            <p className="headline text-xl font-bold flex items-center gap-2">
              <Calculator className="w-5 h-5 text-secondary" /> Try advanced journeys
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
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
          <SurfaceTile>
            <p className="headline text-xl font-bold flex items-center gap-2">
              <Store className="w-5 h-5 text-primary" /> Access & onboarding
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <ActionLink href="/login" variant="ghost" className="text-sm">
                Login
              </ActionLink>
              <ActionLink href="/register" variant="secondary" className="text-sm">
                Register
              </ActionLink>
            </div>
          </SurfaceTile>
        </motion.div>
      </motion.section>

      <motion.div variants={itemVariants}>
        <RbiNotice
          disclaimer="Cred-ible outputs are decision-support insights and must be combined with full lender underwriting under prevailing RBI digital lending guidance."
          retention="Data retention: demo and assessment inputs may be retained for up to 30 days for audits, grievance resolution, and model monitoring."
        />
      </motion.div>
    </motion.div>
  );
}
