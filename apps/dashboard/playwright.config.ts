import { defineConfig, devices } from "@playwright/test";

const apiPort = process.env.WILQ_E2E_API_PORT ?? "8875";
const dashboardPort = process.env.WILQ_E2E_DASHBOARD_PORT ?? "5373";
const apiBaseUrl = `http://127.0.0.1:${apiPort}`;
const dashboardBaseUrl = `http://127.0.0.1:${dashboardPort}`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: {
    timeout: 10_000
  },
  reporter: [["list"]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: dashboardBaseUrl,
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure"
  },
  webServer: [
    {
      command: `uv run uvicorn apps.api.wilq_api.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: "../..",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      url: `${apiBaseUrl}/api/health`
    },
    {
      command: `pnpm --filter @wilq/dashboard dev --host 127.0.0.1 --port ${dashboardPort}`,
      cwd: "../..",
      env: {
        VITE_WILQ_API_BASE_URL: apiBaseUrl
      },
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      url: `${dashboardBaseUrl}/command-center`
    }
  ]
});
