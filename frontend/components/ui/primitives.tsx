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
      className={join("glass-card p-6 sm:p-7 relative overflow-hidden hover:shadow-2xl transition-shadow duration-300", className)}
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
    >
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
      className={join("flat-card p-4 sm:p-5 transition-all duration-300 hover:bg-surface-low/100 hover:border-outline-variant/40", className)}
      whileHover={{ scale: 1.015 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
    >
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
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.95 }}
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
      className="rbi-notice space-y-2 text-sm"
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: 0.1 }}
    >
      <p className="headline text-base font-bold">{title}</p>
      <p className="muted">{disclaimer}</p>
      <p className="text-xs text-slate-300">{retention}</p>
    </motion.section>
  );
}
