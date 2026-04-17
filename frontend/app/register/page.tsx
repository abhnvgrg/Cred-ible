"use client";

import { ActionLink, SurfaceCard } from "@/components/ui/primitives";
import { saveAuthSession, type AuthSession } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

interface RegisterFormState {
  full_name: string;
  work_email: string;
  organization: string;
  password: string;
  confirm_password: string;
}

const INITIAL_STATE: RegisterFormState = {
  full_name: "",
  work_email: "",
  organization: "",
  password: "",
  confirm_password: ""
};

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState<RegisterFormState>(INITIAL_STATE);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (form.password !== form.confirm_password) {
      setErrorMessage("Password and confirm password must match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const session = await apiFetch<AuthSession>("/auth/register", {
        method: "POST",
        body: JSON.stringify(form),
        timeoutMs: 12000
      });
      const saved = saveAuthSession(session);
      if (!saved) {
        throw new Error("Account created but browser session storage is blocked.");
      }
      setSuccessMessage(session.message);
      window.setTimeout(() => router.push("/persona-selection"), 450);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to create account.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <SurfaceCard>
        <span className="eyebrow">Create workspace access</span>
        <h1 className="headline mt-4 text-4xl font-extrabold">
          Join <span className="display-gradient">Cred-ible Control</span>
        </h1>
        <p className="mt-3 text-sm leading-relaxed muted">
          Register your organization profile to run borrower intelligence, scenario simulations, and loan matchmaking.
        </p>

        <form className="mt-6 grid gap-4 sm:grid-cols-2" onSubmit={onSubmit}>
          <label className="form-label sm:col-span-2">
            <span>Full name</span>
            <input
              type="text"
              className="form-input"
              placeholder="Aarav Mehta"
              value={form.full_name}
              onChange={(event) => setForm((prev) => ({ ...prev, full_name: event.target.value }))}
              required
            />
          </label>
          <label className="form-label">
            <span>Work email</span>
            <input
              type="email"
              className="form-input"
              placeholder="aarav@firm.in"
              value={form.work_email}
              onChange={(event) => setForm((prev) => ({ ...prev, work_email: event.target.value }))}
              required
            />
          </label>
          <label className="form-label">
            <span>Organization</span>
            <input
              type="text"
              className="form-input"
              placeholder="FinEdge Capital"
              value={form.organization}
              onChange={(event) => setForm((prev) => ({ ...prev, organization: event.target.value }))}
              required
            />
          </label>
          <label className="form-label">
            <span>Password</span>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                className="form-input pr-11"
                placeholder="••••••••••"
                value={form.password}
                onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
                required
                minLength={8}
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
              >
                {showPassword ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m3 3 18 18" />
                    <path d="M10.58 10.58a2 2 0 0 0 2.83 2.83" />
                    <path d="M9.88 5.09A10.94 10.94 0 0 1 12 4c7 0 10 8 10 8a17.89 17.89 0 0 1-2.16 3.19" />
                    <path d="M6.61 6.61A18.7 18.7 0 0 0 2 12s3 8 10 8a9.74 9.74 0 0 0 5.39-1.61" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2 12s3-8 10-8 10 8 10 8-3 8-10 8-10-8-10-8Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </label>
          <label className="form-label">
            <span>Confirm password</span>
            <div className="relative">
              <input
                type={showConfirmPassword ? "text" : "password"}
                className="form-input pr-11"
                placeholder="••••••••••"
                value={form.confirm_password}
                onChange={(event) => setForm((prev) => ({ ...prev, confirm_password: event.target.value }))}
                required
                minLength={8}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword((prev) => !prev)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                aria-pressed={showConfirmPassword}
              >
                {showConfirmPassword ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m3 3 18 18" />
                    <path d="M10.58 10.58a2 2 0 0 0 2.83 2.83" />
                    <path d="M9.88 5.09A10.94 10.94 0 0 1 12 4c7 0 10 8 10 8a17.89 17.89 0 0 1-2.16 3.19" />
                    <path d="M6.61 6.61A18.7 18.7 0 0 0 2 12s3 8 10 8a9.74 9.74 0 0 0 5.39-1.61" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2 12s3-8 10-8 10 8 10 8-3 8-10 8-10-8-10-8Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </label>
          <button type="submit" className="btn-primary sm:col-span-2" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        {errorMessage ? <p className="mt-4 text-sm text-red-200">{errorMessage}</p> : null}
        {successMessage ? <p className="mt-4 text-sm text-emerald-200">{successMessage}</p> : null}

        <div className="mt-6 flex flex-wrap gap-3">
          <ActionLink href="/login" variant="secondary" className="text-sm">
            Already have access?
          </ActionLink>
          <ActionLink href="/landing-page" variant="ghost" className="text-sm">
            Back to home
          </ActionLink>
        </div>
      </SurfaceCard>
    </div>
  );
}
