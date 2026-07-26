import { expect, test } from "@playwright/test";

const ROUTES = ["/", "/simulator", "/runs", "/compare", "/methodology", "/privacy"];

for (const route of ROUTES) {
  test(`route ${route} loads without console errors`, async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });
    page.on("pageerror", (err) => errors.push(err.message));

    const response = await page.goto(route);
    expect(response?.ok()).toBeTruthy();
    await expect(page.locator("body")).toBeVisible();
    expect(errors, `console errors on ${route}: ${errors.join("\n")}`).toEqual([]);
  });
}

test("footer credits Reints Labs and links to reintslabs.com", async ({ page }) => {
  await page.goto("/");
  const footerLink = page.locator("footer a[href='https://reintslabs.com']").first();
  await expect(footerLink).toBeVisible();
});

test("disclaimer banner is present on every route", async ({ page }) => {
  for (const route of ROUTES) {
    await page.goto(route);
    await expect(page.getByRole("note", { name: "Disclaimer" })).toBeVisible();
  }
});

test("direct navigation and refresh work on a nested SPA route", async ({ page }) => {
  await page.goto("/methodology");
  await expect(page.getByRole("heading", { name: "Methodology" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Methodology" })).toBeVisible();
});

test("no horizontal overflow at 320px width", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  for (const route of ROUTES) {
    await page.goto(route);
    const hasOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(hasOverflow, `${route} overflows horizontally at 320px`).toBe(false);
  }
});
