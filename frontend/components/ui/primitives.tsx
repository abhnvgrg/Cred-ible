import Link from "next/link";
import type { ReactNode } from "react";

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
  const Component = as ?? "section";
  return <Component className={join("glass-card p-6 sm:p-7", className)}>{children}</Component>;
}

export function SurfaceTile({
  children,
  className
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={join("flat-card p-4 sm:p-5", className)}>{children}</div>;
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
    <Link href={href} className={join(baseClass, className)}>
      {children}
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
    <section className="rbi-notice space-y-2 text-sm">
      <p className="headline text-base font-bold">{title}</p>
      <p className="muted">{disclaimer}</p>
      <p className="text-xs text-slate-300">{retention}</p>
    </section>
  );
}
