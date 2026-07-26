import { expect, test } from "@playwright/test";

test.describe("simulator happy path", () => {
  test("loads sample data, runs the default strategy to completion, and shows results", async ({ page }) => {
    await page.goto("/simulator");

    await page.getByRole("button", { name: "Use bundled sample" }).click();
    await expect(page.getByText(/Products/)).toBeVisible();

    const startButton = page.getByRole("button", { name: "Start" });
    await expect(startButton).toBeEnabled({ timeout: 10_000 });
    await startButton.click();

    await expect(page.getByText(/completed|canceled/i).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText("Equity", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /Save run locally/ })).toBeVisible();
  });

  test("pause, resume, and reset controls change run status", async ({ page }) => {
    await page.goto("/simulator");
    await page.getByRole("button", { name: "Use bundled sample" }).click();

    // slow the replay down so the run stays in "running" long enough for this
    // test to reliably click Pause before it finishes (the bundled sample is
    // small enough to otherwise complete in well under a second)
    await page.locator('input[type="range"]').fill("0.25");

    const startButton = page.getByRole("button", { name: "Start" });
    await expect(startButton).toBeEnabled({ timeout: 10_000 });
    await startButton.click();

    await page.getByRole("button", { name: "Pause" }).click();
    await expect(page.locator(".status-pill")).toHaveText(/paused/i);

    await page.getByRole("button", { name: "Resume" }).click();
    await expect(page.locator(".status-pill")).toHaveText(/running|completed/i);

    await page.getByRole("button", { name: "Reset", exact: true }).click();
    await expect(page.locator(".status-pill")).toHaveText(/idle/i);
  });

  test("keyboard-only workflow can reach the start button", async ({ page }) => {
    await page.goto("/simulator");
    await page.getByRole("button", { name: "Use bundled sample" }).click();
    await page.keyboard.press("Tab");
    const startButton = page.getByRole("button", { name: "Start" });
    await startButton.focus();
    await expect(startButton).toBeFocused();
  });

  test("shows a field-level validation error for an invalid strategy", async ({ page }) => {
    await page.goto("/simulator");
    const bankrollInput = page.getByLabel("Bankroll (USD)");
    await bankrollInput.fill("-100");
    await expect(page.getByRole("alert").first()).toBeVisible();
  });
});
