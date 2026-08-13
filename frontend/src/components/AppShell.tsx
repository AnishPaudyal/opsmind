import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/context";
import { Button } from "./Button";

const navigation = [
  { label: "Overview", to: "/" },
  { label: "Products", to: "/products" },
  { label: "Recommendations", to: "/recommendations" },
];

export function AppShell() {
  const { displayName, logout, roles } = useAuth();
  const [logoutFailed, setLogoutFailed] = useState(false);

  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className="sidebar">
        <NavLink aria-label="OpsMind overview" className="brand" to="/">
          <span aria-hidden="true" className="brand__mark">
            O
          </span>
          <span>
            <strong>OpsMind</strong>
            <small>Decision workspace</small>
          </span>
        </NavLink>
        <nav aria-label="Primary navigation" className="primary-nav">
          {navigation.map((item) => (
            <NavLink
              className={({ isActive }) =>
                isActive ? "primary-nav__link is-active" : "primary-nav__link"
              }
              end={item.to === "/"}
              key={item.to}
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="session-card">
          <p className="eyebrow">Signed in</p>
          <strong>{displayName}</strong>
          <p className="session-card__roles">
            {roles.length === 0
              ? "No mapped presentation roles"
              : `${roles.length.toString()} mapped presentation role${roles.length === 1 ? "" : "s"}`}
          </p>
          {logoutFailed ? (
            <p className="inline-error" role="alert">
              Logout could not reach the identity provider. Try again.
            </p>
          ) : null}
          <Button
            onClick={() => {
              setLogoutFailed(false);
              void logout().catch(() => {
                setLogoutFailed(true);
              });
            }}
            variant="quiet"
          >
            Sign out
          </Button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="environment-pill">Foundation workspace</span>
          <span>Phase 8C · Batch 1</span>
        </header>
        <main className="page" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
