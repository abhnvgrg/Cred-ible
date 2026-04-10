"use client";

import { ActionLink, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import { saveAuthSession, type AuthSession } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

interface LoginFormState {
  email: string;
  password: string;
}

const INITIAL_STATE: LoginFormState = {
  email: "",
  password: ""
};

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState<LoginFormState>(INITIAL_STATE);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsSubmitting(true);

    try {
      const session = await apiFetch<AuthSession>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.email.trim(),
          password: form.password
        }),
        timeoutMs: 12000
      });

      const saved = saveAuthSession(session);
      if (!saved) {
        throw new Error("Login succeeded but browser session storage is blocked.");
      }

      setSuccessMessage(session.message);
      window.setTimeout(() => {
        router.push("/persona-selection");
      }, 450);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1fr_0.95fr]">
      <SurfaceCard className="hidden lg:block">
        <span className="eyebrow">Luminal Access</span>
        <h1 className="headline mt-4 text-5xl font-extrabold leading-tight">
          Welcome back to <span className="display-gradient">BharatCredit</span>
        </h1>
        <p className="mt-4 text-base leading-relaxed muted">
          Sign in to review AI score decisions, run simulations, and unlock lender-ready summaries for underserved
          borrowers.
        </p>
        <SurfaceTile className="mt-8">
          <p className="text-sm muted">Secure session controls, audit logs, and RBI-aware decision support included.</p>
        </SurfaceTile>
      </SurfaceCard>

      <SurfaceCard className="max-w-xl">
        <h2 className="headline text-3xl font-extrabold">Sign in</h2>
        <p className="mt-2 text-sm muted">Enter your BharatCredit workspace credentials.</p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <label className="form-label">
            <span>Email address</span>
            <input
              type="email"
              className="form-input"
              placeholder="name@company.com"
              value={form.email}
              onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))}
              required
            />
          </label>
          <label className="form-label">
            <span>Password</span>
            <input
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              required
              minLength={8}
            />
          </label>
          <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {errorMessage ? <p className="mt-4 text-sm text-red-200">{errorMessage}</p> : null}
        {successMessage ? <p className="mt-4 text-sm text-emerald-200">{successMessage}</p> : null}
        <div className="mt-6 flex flex-wrap gap-3">
          <ActionLink href="/register" variant="secondary" className="text-sm">
            Create account
          </ActionLink>
          <ActionLink href="/landing-page" variant="ghost" className="text-sm">
            Back to home
          </ActionLink>
        </div>
      </SurfaceCard>
    </div>
  );
}
