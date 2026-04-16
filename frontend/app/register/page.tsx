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
            <input
              type="password"
              className="form-input"
              placeholder="••••••••••"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              required
              minLength={8}
            />
          </label>
          <label className="form-label">
            <span>Confirm password</span>
            <input
              type="password"
              className="form-input"
              placeholder="••••••••••"
              value={form.confirm_password}
              onChange={(event) => setForm((prev) => ({ ...prev, confirm_password: event.target.value }))}
              required
              minLength={8}
            />
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
