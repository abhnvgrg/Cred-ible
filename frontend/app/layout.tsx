import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import Link from "next/link";
import type { ReactNode } from "react";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter"
});

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta"
});

export const metadata: Metadata = {
  title: "BharatCredit",
  description: "BharatCredit alternative credit intelligence"
};

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${plusJakartaSans.variable}`}>
        <div className="app-shell">
          <header className="app-header">
            <div className="app-header-inner">
              <Link href="/landing-page" className="brand-mark">
                BharatCredit
              </Link>
              <nav className="app-nav">
                <Link href="/credit-dashboard" className="app-nav-link">
                  Dashboard
                </Link>
                <Link href="/what-if-analysis" className="app-nav-link">
                  Analytics
                </Link>
                <Link href="/ai-processing" className="app-nav-link">
                  Simulations
                </Link>
                <Link href="/loan-marketplace" className="app-nav-link">
                  Marketplace
                </Link>
              </nav>
              <div className="header-actions">
                <Link href="/login" className="btn-ghost text-xs sm:text-sm">
                  Login
                </Link>
                <Link href="/register" className="btn-secondary text-xs sm:text-sm">
                  Register
                </Link>
              </div>
            </div>
          </header>
          <main className="page-shell">{children}</main>
        </div>
      </body>
    </html>
  );
}
