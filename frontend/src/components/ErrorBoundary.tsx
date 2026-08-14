import { Component, type ReactNode } from "react";

import { ErrorState } from "./States";

export class ErrorBoundary extends Component<
  { readonly children: ReactNode },
  { readonly failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  componentDidCatch(): void {
    // Deliberately do not log render errors: provider payloads and tokens must never
    // reach an uncontrolled browser logging sink.
  }

  render(): ReactNode {
    if (this.state.failed) {
      return (
        <main className="centered-page" id="main-content">
          <ErrorState title="The workspace could not render">
            <p>
              Reload the page. If the problem continues, return to the sign-in page.
            </p>
          </ErrorState>
        </main>
      );
    }
    return this.props.children;
  }
}
