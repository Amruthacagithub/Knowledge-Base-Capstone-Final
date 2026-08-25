import { test, expect } from "@playwright/test";

const E2E_EMAIL = process.env.PLAYWRIGHT_LOGIN_EMAIL || "harshini@company.com";
const E2E_PASSWORD = process.env.PLAYWRIGHT_LOGIN_PASSWORD || process.env.SMOKE_API_PASSWORD || "";

test.describe("Trust-RAG local UI", () => {
  test.skip(
    !process.env.PLAYWRIGHT_RUN_E2E,
    "Set PLAYWRIGHT_RUN_E2E=1 with backend and frontend running to execute browser tests.",
  );

  test("login page renders", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  });

  test("login and search returns an answer", async ({ page }) => {
    test.skip(!E2E_PASSWORD, "Set PLAYWRIGHT_LOGIN_PASSWORD or SMOKE_API_PASSWORD for login e2e.");

    await page.goto("/");
    await page.locator("#work-email").fill(E2E_EMAIL);
    await page.locator("#work-password").fill(E2E_PASSWORD);
    await page.getByRole("button", { name: /continue/i }).click();

    await expect(page.getByPlaceholder("Ask a question…")).toBeVisible({ timeout: 30_000 });
    await page.getByPlaceholder("Ask a question…").fill("How many PTO days do employees receive?");
    await page.locator("button.send-btn").click();

    await expect(page.locator(".chat-turn .a-card")).toBeVisible({
      timeout: 120_000,
    });
  });

  test("mobile layout avoids horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    );
    expect(overflow).toBeTruthy();
  });
});
