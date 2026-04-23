import Link from "next/link";

const footerSections = [
  {
    title: "Product",
    links: [
      { label: "Credit Dashboard", href: "/credit-dashboard" },
      { label: "What-if Analysis", href: "/what-if-analysis" },
      { label: "AI Processing", href: "/ai-processing" },
      { label: "Loan Marketplace", href: "/loan-marketplace" }
    ]
  },
  {
    title: "Company",
    links: [
      { label: "About Cred-ible", href: "/landing-page" },
      { label: "Team / Organization", href: "/landing-page" },
      { label: "Billing / Subscription", href: "/loan-marketplace" },
      { label: "Careers", href: "/landing-page" }
    ]
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", href: "/landing-page" },
      { label: "Help Center", href: "/landing-page" },
      { label: "System Status", href: "/result" },
      { label: "API Integrations", href: "/ai-processing" }
    ]
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "/landing-page" },
      { label: "Terms of Service", href: "/landing-page" },
      { label: "Cookie Policy", href: "/landing-page" },
      { label: "Security", href: "/landing-page" }
    ]
  }
];

export function AppFooter() {
  return (
    <footer className="border-t border-outline-variant/30 bg-slate-950/70 backdrop-blur-xl">
      <div className="mx-auto w-full max-w-[1180px] px-4 py-10 md:px-5 md:py-12">
        <div className="grid gap-8 md:grid-cols-[1.2fr_2fr]">
          <section className="space-y-4">
            <Link
              href="/"
              className="inline-block text-2xl leading-none font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400"
            >
              Cred-ible
            </Link>
            <p className="text-sm text-slate-300 max-w-sm">
              Alternative credit intelligence platform for risk scoring, lending operations, and compliant borrower insights.
            </p>
            <div className="space-y-1 text-sm text-slate-300">
              <p>
                <span className="text-slate-400">Contact:</span>{" "}
                <a className="text-indigo-200 hover:text-white" href="mailto:support@credible.ai">
                  support@credible.ai
                </a>
              </p>
              <p>
                <span className="text-slate-400">Phone:</span>{" "}
                <a className="text-indigo-200 hover:text-white" href="tel:+911800123456">
                  +91 1800 123 456
                </a>
              </p>
              <p>
                <span className="text-slate-400">Address:</span> Noida, Uttar Pradesh, India
              </p>
            </div>
          </section>
          <section className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            {footerSections.map((section) => (
              <div key={section.title}>
                <h3 className="text-sm font-semibold text-indigo-100">{section.title}</h3>
                <ul className="mt-3 space-y-2">
                  {section.links.map((link) => (
                    <li key={link.label}>
                      <Link href={link.href} className="text-sm text-slate-300 hover:text-white transition-colors">
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
        </div>
        <div className="mt-8 pt-4 border-t border-indigo-300/15 flex flex-col gap-2 text-xs text-slate-400 md:flex-row md:items-center md:justify-between">
          <p>© {new Date().getFullYear()} Cred-ible. All rights reserved.</p>
          <p>
            By using this platform, you agree to our{" "}
            <Link href="/landing-page" className="text-indigo-200 hover:text-white">
              Privacy Policy
            </Link>{" "}
            and{" "}
            <Link href="/landing-page" className="text-indigo-200 hover:text-white">
              Terms
            </Link>
            .
          </p>
        </div>
      </div>
    </footer>
  );
}
