"use client";

import { ActionLink, RbiNotice, SurfaceCard, SurfaceTile } from "@/components/ui/primitives";
import { useEffect, useMemo, useState } from "react";

type Persona = {
  id: string;
  name: string;
  profile: string;
};

const PERSONA_ORDER = ["raju", "priya", "mohammed"] as const;

const FALLBACK_PERSONAS: Record<(typeof PERSONA_ORDER)[number], Persona> = {
  raju: { id: "raju", name: "Raju", profile: "Vegetable vendor with stable daily cashflow" },
  priya: { id: "priya", name: "Priya", profile: "Freelance designer with uneven monthly billing" },
  mohammed: { id: "mohammed", name: "Mohammed", profile: "Shop owner balancing growth and repayments" }
};

function normalizePersonas(personas: Persona[]): Persona[] {
  const byId = new Map(
    personas
      .filter((persona) => persona.id && persona.name && persona.profile)
      .map((persona) => [persona.id.toLowerCase(), { ...persona, id: persona.id.toLowerCase() }])
  );

  return PERSONA_ORDER.map((id) => byId.get(id) ?? FALLBACK_PERSONAS[id]);
}

function personaTag(personaId: string) {
  if (personaId === "raju") return "High stability";
  if (personaId === "priya") return "Variable income";
  return "Moderate risk";
}

export default function DemoPage() {
  const [personas, setPersonas] = useState<Persona[]>(() => normalizePersonas([]));
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let isCancelled = false;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), 8000);

    async function loadPersonas() {
      try {
        const response = await fetch("/api/personas", {
          cache: "no-store",
          signal: controller.signal
        });
        if (!response.ok) {
          throw new Error("Unable to load personas");
        }

        const payload = (await response.json()) as { personas?: Persona[] };
        const fetchedPersonas = normalizePersonas(payload.personas ?? []);

        if (!isCancelled) {
          setPersonas(fetchedPersonas);
          setErrorMessage(null);
        }
      } catch {
        if (!isCancelled) {
          setPersonas(normalizePersonas([]));
          setErrorMessage(
            "Live personas are temporarily unavailable. Default demo personas are shown for continuity."
          );
        }
      } finally {
        window.clearTimeout(timer);
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadPersonas();

    return () => {
      isCancelled = true;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [refreshKey]);

  const content = useMemo(() => {
    if (isLoading) {
      return (
        <SurfaceCard className="text-sm muted">
          <p>Loading persona profiles from Cred-ible API...</p>
        </SurfaceCard>
      );
    }

    return (
      <section className="grid gap-4 md:grid-cols-3">
        {personas.map((persona) => (
          <SurfaceTile key={persona.id} className="flex h-full flex-col justify-between">
            <div>
              <span className="status-pill bg-primary/20 text-primary">{personaTag(persona.id)}</span>
              <h2 className="headline mt-4 text-2xl font-bold">{persona.name}</h2>
              <p className="mt-2 text-sm leading-relaxed muted">{persona.profile}</p>
            </div>
              <ActionLink
                href={`/ai-processing?persona=${encodeURIComponent(persona.id)}&source=demo`}
                className="mt-6 w-full text-sm"
              >
                Run AI scoring
            </ActionLink>
          </SurfaceTile>
        ))}
      </section>
    );
  }, [isLoading, personas]);

  return (
    <div className="space-y-6">
      <SurfaceCard>
        <span className="eyebrow">Interactive simulation</span>
        <h1 className="headline mt-4 text-4xl font-extrabold">Choose a borrower persona</h1>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed muted sm:text-base">
          Each profile maps to the same processing pipeline used by Cred-ible. Live API data is used when
          available, with graceful fallback to trusted local persona defaults.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <ActionLink href="/landing-page" variant="ghost" className="text-sm">
            Back to home
          </ActionLink>
          <ActionLink href="/intake" variant="secondary" className="text-sm">
            Switch to intake form
          </ActionLink>
        </div>
      </SurfaceCard>

      {errorMessage ? (
        <SurfaceTile className="border border-amber-400/30">
          <p className="text-sm text-amber-200">{errorMessage}</p>
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              setRefreshKey((current) => current + 1);
            }}
            className="btn-secondary mt-4 text-sm"
          >
            Retry live personas
          </button>
        </SurfaceTile>
      ) : null}

      {content}

      <RbiNotice
        disclaimer="Persona scores are for demo and decision-support purposes only. Production lending decisions must apply complete underwriting and RBI policy controls."
        retention="Data retention: persona simulation logs may be retained for up to 30 days for auditability, model governance, and support."
      />
    </div>
  );
}
