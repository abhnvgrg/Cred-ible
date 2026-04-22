"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  href: string;
  label: string;
  isActive: (pathname: string) => boolean;
};

const navItems: NavItem[] = [
  {
    href: "/credit-dashboard",
    label: "Dashboard",
    isActive: (pathname) => pathname === "/credit-dashboard"
  },
  {
    href: "/what-if-analysis",
    label: "Analytics",
    isActive: (pathname) => pathname === "/what-if-analysis" || pathname === "/what-if"
  },
  {
    href: "/ai-processing",
    label: "Simulations",
    isActive: (pathname) =>
      pathname === "/ai-processing" ||
      pathname === "/processing" ||
      pathname === "/intake" ||
      pathname === "/persona-selection" ||
      pathname === "/demo"
  },
  {
    href: "/loan-marketplace",
    label: "Loans",
    isActive: (pathname) => pathname === "/loan-marketplace" || pathname === "/marketplace"
  }
];

export function AppHeader() {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  return (
    <>
      <header className="app-header">
        <div className="app-header-inner grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 md:gap-6">
          <Link
            href="/"
            className="text-2xl md:text-[1.75rem] leading-none font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400"
          >
            Cred-ible
          </Link>

          <nav className="hidden md:flex items-center justify-center gap-2 text-sm text-gray-400">
            {navItems.map((item) => {
              const active = item.isActive(pathname);
              const baseClass =
                "rounded-full border border-dashed px-3 py-1.5 font-semibold transition-all duration-200";
              const activeClass = "text-indigo-200 border-indigo-400/45 bg-indigo-500/12 shadow-[0_0_14px_rgba(129,140,248,0.35)]";
              const inactiveClass =
                "text-gray-400 border-indigo-500/0 hover:text-white hover:border-indigo-500/35 hover:bg-indigo-500/8 hover:shadow-[0_0_12px_rgba(129,140,248,0.25)]";

              return (
                <Link key={item.href} href={item.href} className={`${baseClass} ${active ? activeClass : inactiveClass}`}>
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center justify-end gap-4 text-gray-400">
            <div className="hidden md:flex items-center gap-4">
              <button className="hover:text-white transition-colors" aria-label="Notifications">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                  <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                </svg>
              </button>
              <button className="hover:text-white transition-colors" aria-label="Settings">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              </button>
              <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center overflow-hidden">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#94a3b8"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </div>
            </div>
            <button
              type="button"
              aria-label="Toggle navigation menu"
              aria-expanded={isMobileMenuOpen}
              className="inline-flex md:hidden items-center justify-center rounded-xl border border-indigo-400/20 bg-indigo-400/10 p-2.5 text-indigo-100 transition-colors hover:bg-indigo-400/20"
              onClick={() => setIsMobileMenuOpen((previous) => !previous)}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                {isMobileMenuOpen ? (
                  <>
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </>
                ) : (
                  <>
                    <line x1="3" y1="6" x2="21" y2="6" />
                    <line x1="3" y1="12" x2="21" y2="12" />
                    <line x1="3" y1="18" x2="21" y2="18" />
                  </>
                )}
              </svg>
            </button>
          </div>
        </div>
      </header>
      <div
        className={`fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-[2px] transition-opacity duration-300 md:hidden ${
          isMobileMenuOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={() => setIsMobileMenuOpen(false)}
      />
      <aside
        className={`fixed left-0 top-0 z-50 flex h-dvh w-[80vw] max-w-[320px] flex-col border-r border-indigo-200/20 bg-gradient-to-b from-slate-900/60 via-slate-950/55 to-slate-950/70 p-5 shadow-[0_26px_80px_rgba(0,0,0,0.5)] backdrop-blur-2xl transition-transform duration-300 ease-out md:hidden ${
          isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-indigo-200/15 pb-4">
          <Link
            href="/"
            className="text-xl leading-none font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400"
          >
            Cred-ible
          </Link>
          <button
            type="button"
            aria-label="Close navigation menu"
            className="rounded-lg border border-indigo-300/20 bg-indigo-300/10 p-2 text-indigo-100 transition-colors hover:bg-indigo-300/20"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <nav className="mt-5 flex flex-1 flex-col gap-2">
          {navItems.map((item) => {
            const active = item.isActive(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-xl border px-4 py-3 text-sm font-semibold transition-all duration-200 ${
                  active
                    ? "border-indigo-400/45 bg-indigo-500/20 text-indigo-100 shadow-[0_0_14px_rgba(129,140,248,0.35)]"
                    : "border-indigo-400/0 bg-transparent text-slate-300 hover:border-indigo-400/30 hover:bg-indigo-500/10 hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-4 flex items-center gap-3 border-t border-indigo-200/15 pt-4">
          <button
            type="button"
            aria-label="Settings"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-300/20 bg-indigo-300/10 text-indigo-100 transition-colors hover:bg-indigo-300/20"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
          <button
            type="button"
            aria-label="Profile"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-indigo-300/20 bg-indigo-300/10 text-indigo-100 transition-colors hover:bg-indigo-300/20"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </button>
        </div>
      </aside>
    </>
  );
}
