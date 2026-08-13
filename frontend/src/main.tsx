import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { ErrorState } from "./components/States";
import { loadPublicConfig } from "./config";
import "./styles/main.css";

const rootElement = document.getElementById("root");
if (rootElement === null) {
  throw new Error("OpsMind root element is missing");
}

const root = createRoot(rootElement);
try {
  const config = loadPublicConfig();
  root.render(
    <StrictMode>
      <App config={config} />
    </StrictMode>,
  );
} catch {
  root.render(
    <main className="centered-page" id="main-content">
      <ErrorState title="OpsMind is not configured">
        <p>The required public application settings are missing or invalid.</p>
      </ErrorState>
    </main>,
  );
}
