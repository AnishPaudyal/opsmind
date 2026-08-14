import { defineConfig, devices } from "@playwright/test";

const publicEnvironment = {
  VITE_OPSMIND_API_BASE_URL: "http://127.0.0.1:8000",
  VITE_OPSMIND_ENVIRONMENT: "test",
  VITE_OPSMIND_ZITADEL_ISSUER: "https://opsmind-phase-8b-gl9aih.us1.zitadel.cloud",
  VITE_OPSMIND_ZITADEL_PROJECT_ID: "386124341898709869",
  VITE_OPSMIND_ZITADEL_CLIENT_ID: "386124342116795580",
};

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  ...(process.env.CI ? { workers: 1 } : {}),
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173/login",
    reuseExistingServer: !process.env.CI,
    env: {
      ...process.env,
      ...publicEnvironment,
    },
  },
});
