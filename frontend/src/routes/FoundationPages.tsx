import { Link } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { BackendWakingState, ForbiddenState } from "../components/States";

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
