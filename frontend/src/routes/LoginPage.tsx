import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../auth/context";
import { boundedReturnPath } from "../auth/service";
import { Button } from "../components/Button";

export function LoginPage() {
  const auth = useAuth();
  const location = useLocation();
  const [failed, setFailed] = useState(false);
  const returnTo = boundedReturnPath(
    (location.state as { from?: unknown } | null)?.from,
  );

  if (auth.status === "authenticated") {
    return <Navigate replace to={returnTo} />;
  }

  return (
    <main className="login-page" id="main-content">
      <section className="login-panel">
        <div className="brand brand--login">
          <span aria-hidden="true" className="brand__mark">
            O
          </span>
          <span>
            <strong>OpsMind</strong>
            <small>Supply-chain decision intelligence</small>
          </span>
        </div>
        <p className="eyebrow">Authenticated portfolio workspace</p>
        <h1>Decisions backed by visible operational evidence.</h1>
        <p className="login-panel__lede">
          Inspect products, demand, forecast evidence, inventory exposure, and
          recommendation decisions in one bounded workflow.
        </p>
        <ul className="feature-list">
          <li>Authorization Code with PKCE</li>
          <li>Backend-enforced permissions</li>
          <li>Audited recommendation decisions</li>
        </ul>
        {failed ? (
          <p className="inline-error" role="alert">
            Sign-in could not start. No session data was retained.
          </p>
        ) : null}
        <Button
          disabled={auth.status === "loading"}
          onClick={() => {
            setFailed(false);
            void auth.login(returnTo).catch(() => {
              setFailed(true);
            });
          }}
        >
          Continue with ZITADEL
        </Button>
        <p className="fine-print">
          OpsMind never asks for or stores your identity-provider password.
        </p>
      </section>
      <aside aria-label="Product context" className="login-context">
        <p className="eyebrow">From signal to decision</p>
        <div className="workflow-stack" aria-label="OpsMind workflow stages">
          <span>Demand signal</span>
          <span>Forecast evidence</span>
          <span>Stockout exposure</span>
          <span>Reorder decision</span>
          <span>Audit history</span>
        </div>
      </aside>
    </main>
  );
}
