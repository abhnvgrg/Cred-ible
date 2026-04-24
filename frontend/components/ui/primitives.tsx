"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { motion } from "framer-motion";

function join(...classes: Array<string | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function SurfaceCard({
  children,
  className,
  as
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "article" | "div";
}) {
  const Component = motion[as ?? "section"] as any;
  return (
    <Component 
      className={join("glass-card p-6 sm:p-8 relative overflow-hidden transition-all duration-300", className)}
      whileHover={{ y: -6 }}
      transition={{ type: "spring", stiffness: 350, damping: 25 }}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-white/[0.04] to-transparent pointer-events-none opacity-0 hover:opacity-100 transition-opacity duration-500" />
      {children}
    </Component>
  );
}

export function SurfaceTile({
  children,
  className
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div 
      className={join("flat-card p-5 sm:p-6 transition-all duration-300 hover:bg-white/[0.04] hover:border-white/[0.08] hover:shadow-[0_8px_32px_rgba(0,0,0,0.4)] relative overflow-hidden", className)}
      whileHover={{ y: -2 }}
      transition={{ type: "spring", stiffness: 450, damping: 30 }}
    >
      <div className="absolute inset-0 bg-gradient-to-b from-white/[0.04] to-transparent opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
      {children}
    </motion.div>
  );
}

export function ActionLink({
  href,
  children,
  variant = "primary",
  className
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost";
  className?: string;
}) {
  const baseClass = variant === "primary" ? "btn-primary" : variant === "secondary" ? "btn-secondary" : "btn-ghost";
  
  return (
    <Link href={href} legacyBehavior passHref>
      <motion.a 
        className={join(baseClass, className)}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.96 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
      >
        {children}
      </motion.a>
    </Link>
  );
}

export function RbiNotice({
  title = "RBI compliance notice",
  disclaimer,
  retention
}: {
  title?: string;
  disclaimer: string;
  retention: string;
}) {
  return (
    <motion.section 
      className="rbi-notice space-y-2 text-sm relative overflow-hidden group hover:border-white/[0.08] transition-colors duration-300"
      initial={{ opacity: 0, y: 15 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="absolute top-0 right-0 p-3 opacity-5 group-hover:opacity-10 transition-opacity duration-300">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
      </div>
      <p className="headline text-base font-bold text-slate-300 tracking-tight">{title}</p>
      <p className="text-slate-400 leading-relaxed">{disclaimer}</p>
      <p className="text-xs text-slate-500 pt-1">{retention}</p>
    </motion.section>
  );
}
