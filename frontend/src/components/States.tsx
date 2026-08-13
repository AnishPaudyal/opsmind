import type { ReactNode } from "react";

function StatePanel({
  children,
  eyebrow,
  title,
  tone = "neutral",
}: {
  readonly children: ReactNode;
  readonly eyebrow: string;
  readonly title: string;
  readonly tone?: "neutral" | "warning" | "danger";
}) {
  return (
    <section
      aria-live={tone === "danger" ? "assertive" : "polite"}
      className={`state-panel state-panel--${tone}`}
    >
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <div className="state-panel__body">{children}</div>
    </section>
  );
}

export function LoadingState({
  label = "Loading OpsMind",
}: {
  readonly label?: string;
}) {
  return (
    <div aria-busy="true" aria-live="polite" className="loading-state" role="status">
      <span aria-hidden="true" className="loading-state__indicator" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({
  children,
  title,
}: {
  readonly children: ReactNode;
  readonly title: string;
}) {
  return (
    <StatePanel eyebrow="Nothing here yet" title={title}>
      {children}
    </StatePanel>
  );
}

export function ErrorState({
  children,
  title = "Something went wrong",
}: {
  readonly children: ReactNode;
  readonly title?: string;
}) {
  return (
    <StatePanel eyebrow="Request failed" title={title} tone="danger">
      {children}
    </StatePanel>
  );
}

export function ForbiddenState() {
  return (
    <StatePanel
      eyebrow="Access limited"
      title="This action is not available"
      tone="warning"
    >
      <p>
        Your session is valid, but the API did not grant the permission required for
        this action. OpsMind always treats the backend as the authorization authority.
      </p>
    </StatePanel>
  );
}

export function BackendWakingState() {
  return (
    <StatePanel
      eyebrow="Free service wake-up"
      title="The API may be starting"
      tone="warning"
    >
      <p>
        The portfolio backend can sleep when idle. Safe reads may be retried twice;
        write and decision requests are never replayed automatically.
      </p>
    </StatePanel>
  );
}
