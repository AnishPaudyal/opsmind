import { Link, useParams } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { BackendWakingState, EmptyState, ForbiddenState } from "../components/States";

function FoundationPanel({ children }: { readonly children: React.ReactNode }) {
  return (
    <section className="foundation-panel">
      <p className="eyebrow">Batch 1 foundation</p>
      {children}
    </section>
  );
}

export function OverviewPage() {
  return (
    <>
      <PageHeader
        description="A calm operational workspace for the product-to-decision evidence chain."
        eyebrow="Operational overview"
        title="Know what needs attention—and why."
      />
      <div className="metric-grid" aria-label="Future overview metrics">
        {[
          ["Products", "Contract foundation ready"],
          ["Exposure", "Deterministic evidence"],
          ["Reviews", "Audited state"],
        ].map(([label, value]) => (
          <section className="metric-card" key={label}>
            <p>{label}</p>
            <strong>{value}</strong>
          </section>
        ))}
      </div>
      <FoundationPanel>
        <h2>Workflow surfaces are intentionally bounded</h2>
        <p>
          Batch 1 establishes routing, authentication, typed transport, and reusable
          states. Real operational data and actions arrive in the separately gated Batch
          2; this page does not fabricate backend results.
        </p>
      </FoundationPanel>
    </>
  );
}

export function ProductsPage() {
  return (
    <>
      <PageHeader
        description="Browse normalized product records and move into one evidence workspace."
        eyebrow="Products"
        title="Operational catalog"
      />
      <EmptyState title="Product data is not connected in Batch 1">
        <p>
          The generated product contract is ready. Listing, creation, and live loading
          behavior remain part of Batch 2.
        </p>
      </EmptyState>
    </>
  );
}

export function ProductDetailPage() {
  const { productId } = useParams();
  return (
    <>
      <PageHeader
        description="Inventory, demand, forecast, exposure, and recommendation evidence will compose here."
        eyebrow="Product workspace"
        title="Product evidence chain"
      />
      <FoundationPanel>
        <h2>Deep-link contract established</h2>
        <p>
          Requested product identifier: <code>{productId}</code>
        </p>
        <p>No product lookup or mutation is simulated in this foundation.</p>
      </FoundationPanel>
    </>
  );
}

export function RecommendationsPage() {
  return (
    <>
      <PageHeader
        description="Reconstruct pending and terminal review work from durable backend state."
        eyebrow="Recommendations"
        title="Decision review queue"
      />
      <EmptyState title="The review queue requires the Batch 2 list endpoint">
        <p>
          Existing reviews can currently be addressed only by UUID. OpsMind does not
          fake a queue while the reviewed collection endpoint remains deferred.
        </p>
      </EmptyState>
    </>
  );
}

export function RecommendationDetailPage() {
  const { recommendationId } = useParams();
  return (
    <>
      <PageHeader
        description="Immutable recommendation evidence, terminal decision controls, and audit history belong here."
        eyebrow="Recommendation review"
        title="Decision evidence"
      />
      <FoundationPanel>
        <h2>Deep-link contract established</h2>
        <p>
          Requested recommendation: <code>{recommendationId}</code>
        </p>
        <p>Approval and rejection remain unimplemented until Batch 2.</p>
      </FoundationPanel>
    </>
  );
}

export function ForbiddenPage() {
  return (
    <>
      <PageHeader
        description="Authentication succeeded, but the backend remains the authority for every action."
        eyebrow="Authorization"
        title="Permission required"
      />
      <ForbiddenState />
    </>
  );
}

export function UnavailablePage() {
  return (
    <>
      <PageHeader
        description="Free portfolio services may need a bounded wake-up interval after inactivity."
        eyebrow="Service status"
        title="OpsMind is temporarily unavailable"
      />
      <BackendWakingState />
    </>
  );
}

export function NotFoundPage() {
  return (
    <>
      <PageHeader
        description="The browser route does not match an OpsMind workspace surface."
        eyebrow="Not found"
        title="There is no page at this address"
      />
      <Link className="text-link" to="/">
        Return to overview
      </Link>
    </>
  );
}
