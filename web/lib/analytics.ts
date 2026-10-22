import posthog from "posthog-js";

type Events = {
  tiss_playground_validate: { resultado: "valido" | "com_achados" | "erro" };
  tiss_copy_snippet: { pagina: string };
  tiss_cta_github: { local: string };
  tiss_calculator_use: {
    faturamento: string;
    percentual: string;
    glosa: string;
    recorridas: string;
    valor_medio: string;
  };
  tiss_operadora_contact: { local: string };
};

let started = false;

export function startAnalytics(): void {
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key || started) return;
  posthog.init(key, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com",
    autocapture: false,
    capture_pageview: false,
    capture_pageleave: false,
    disable_session_recording: true,
    persistence: "memory",
    person_profiles: "identified_only",
    advanced_disable_flags: true,
    disable_surveys: true,
    before_send: (event) => {
      for (const [key, value] of Object.entries(event.properties)) {
        if (typeof value !== "string" || !/url|referrer/i.test(key)) continue;
        const index = value.search(/[?#]/);
        if (index !== -1) event.properties[key] = value.slice(0, index);
      }
      return event;
    },
  });
  started = true;
}

export function track<E extends keyof Events>(event: E, props: Events[E]): void {
  if (!started) return;
  posthog.capture(event, props, { send_instantly: true });
}
