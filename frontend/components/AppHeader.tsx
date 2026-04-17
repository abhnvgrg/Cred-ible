"use client";

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

  return (
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
      </div>
    </header>
  );
}
