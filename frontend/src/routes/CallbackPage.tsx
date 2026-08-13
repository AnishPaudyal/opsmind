import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/context";
import { ErrorState, LoadingState } from "../components/States";

export function CallbackPage() {
  const { completeLogin } = useAuth();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    void completeLogin()
      .then((returnTo) => {
        if (active) {
          void navigate(returnTo, { replace: true });
        }
      })
      .catch(() => {
        if (active) {
          setFailed(true);
        }
      });
    return () => {
      active = false;
    };
  }, [completeLogin, navigate]);

  return (
    <main className="centered-page" id="main-content">
      {failed ? (
        <ErrorState title="Sign-in could not be completed">
          <p>The callback was rejected safely. Restart sign-in from OpsMind.</p>
          <Link className="text-link" replace to="/login">
            Return to sign in
          </Link>
        </ErrorState>
      ) : (
        <LoadingState label="Completing secure sign-in" />
      )}
    </main>
  );
}
