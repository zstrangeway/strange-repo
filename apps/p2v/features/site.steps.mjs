import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import {
  After,
  AfterAll,
  Before,
  BeforeAll,
  Given,
  When,
  Then,
  setDefaultTimeout,
} from "@cucumber/cucumber";
import { chromium } from "playwright";

setDefaultTimeout(30_000);
let server;
let browser;
let origin;

BeforeAll(async function () {
  server = spawn(
    "python3",
    [
      "-u",
      "-m",
      "http.server",
      "0",
      "--bind",
      "127.0.0.1",
      "--directory",
      process.env.P2V_TEST_DIRECTORY || "out",
    ],
    { stdio: ["ignore", "pipe", "pipe"] },
  );
  origin = await new Promise((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error("P2V static server did not start")),
      10_000,
    );
    let output = "";
    server.stdout.on("data", (chunk) => {
      output += chunk;
      const match = output.match(/port (\d+)/);
      if (match) {
        clearTimeout(timeout);
        resolve(`http://127.0.0.1:${match[1]}`);
      }
    });
    server.on("error", (error) => {
      clearTimeout(timeout);
      reject(error);
    });
    server.on("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`Static server exited ${code}: ${output}`));
    });
    server.stderr.on("data", () => {});
  });
  browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
      : {}),
  });
});

AfterAll(async function () {
  await browser?.close();
  server?.kill();
});

Before(async function () {
  this.context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
  });
  this.page = await this.context.newPage();
  this.errors = [];
  this.page.on("pageerror", (error) => this.errors.push(error.message));
  this.page.on("console", (message) => {
    if (message.type() === "error") this.errors.push(message.text());
  });
});

After(async function () {
  await this.context?.close();
  assert.deepEqual(this.errors, [], "No browser runtime or hydration errors");
});

Given("I use a mobile screen", async function () {
  await this.page.setViewportSize({ width: 390, height: 844 });
});
When("I use a desktop screen", async function () {
  await this.page.setViewportSize({ width: 1440, height: 1000 });
  await this.page.waitForFunction(
    () => getComputedStyle(document.querySelector(".menu")).display === "none",
  );
});
When("I open {string}", async function (path) {
  const response = await this.page.goto(origin + path);
  assert.equal(response.status(), 200);
  await this.page.waitForLoadState("networkidle");
});
Then("the main heading contains {string}", async function (heading) {
  assert.ok(
    (await this.page.locator("main h1").textContent()).includes(heading),
  );
});
Then(
  "the page has its title, description, and noindex metadata",
  async function () {
    assert.match(await this.page.title(), /P2V Basketball Academy/);
    assert.ok(
      (
        await this.page
          .locator('meta[name="description"]')
          .getAttribute("content")
      ).length > 40,
    );
    assert.match(
      await this.page.locator('meta[name="robots"]').getAttribute("content"),
      /noindex/,
    );
    assert.match(
      await this.page.locator('meta[name="robots"]').getAttribute("content"),
      /nofollow/,
    );
  },
);
Then("all page images load", async function () {
  const failures = await this.page.evaluate(async () => {
    const images = [...document.images];
    images.forEach((image) => {
      image.loading = "eager";
    });
    await Promise.all(images.map((image) => image.decode().catch(() => {})));
    return images
      .filter((image) => !image.naturalWidth)
      .map((image) => image.src);
  });
  assert.deepEqual(failures, []);
});
Then("the page fits a mobile screen", async function () {
  await this.page.setViewportSize({ width: 390, height: 844 });
  assert.ok(
    await this.page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
    "No horizontal overflow on mobile",
  );
});
When("I open the menu", async function () {
  await this.page.getByRole("button", { name: "Menu" }).click();
  await this.page.waitForFunction(
    () =>
      document.querySelector(".menu").getAttribute("aria-expanded") === "true",
  );
});
When("I press {string}", async function (key) {
  await this.page.keyboard.press(key);
});
Then("the menu is closed", async function () {
  await this.page.waitForFunction(
    () =>
      document.querySelector(".menu").getAttribute("aria-expanded") === "false",
  );
});
Then("the menu is closed and focused", async function () {
  await this.page.waitForFunction(
    () =>
      document.querySelector(".menu").getAttribute("aria-expanded") ===
        "false" && document.activeElement === document.querySelector(".menu"),
  );
});
When("I follow {string} in the navigation", async function (label) {
  await this.page
    .getByRole("navigation")
    .getByRole("link", { name: label, exact: true })
    .click();
  await this.page.waitForLoadState("networkidle");
});
Then("{string} is the current navigation page", async function (label) {
  await this.page.waitForFunction(
    (expected) =>
      document
        .querySelector('nav a[aria-current="page"]')
        ?.textContent.trim() === expected,
    label,
  );
});
When("I choose the {string} training tab", async function (label) {
  await this.page.getByRole("tab", { name: label }).click();
});
Then("the training panel shows {string}", async function (title) {
  const panel = this.page.getByRole("tabpanel");
  await panel.getByRole("heading", { name: title, exact: true }).waitFor();
  const selected = this.page.getByRole("tab", { selected: true });
  assert.equal(await selected.count(), 1);
  assert.equal(await selected.getAttribute("tabindex"), "0");
  assert.equal(
    await panel.getAttribute("aria-labelledby"),
    await selected.getAttribute("id"),
  );
  assert.equal(
    await selected.evaluate((element) => element === document.activeElement),
    true,
  );
});
Then("the inquiry interest is {string}", async function (interest) {
  await this.page.waitForFunction(
    (expected) =>
      document.querySelector('select[name="interest"]').value === expected,
    interest,
  );
});

async function fillInquiry(world, withAthlete) {
  await world.page.locator('[name="name"]').fill("  Sam O’Neil & Lee  ");
  await world.page.locator('[name="email"]').fill("sam@example.com");
  if (withAthlete) {
    await world.page.locator('[name="athlete"]').fill("Jordan");
    await world.page.locator('[name="age"]').fill("14");
  }
  await world.page
    .locator('[name="message"]')
    .fill(
      "We’d like training & camps. <script>Is Saturday available?</script>",
    );
}
When("I complete the inquiry form", async function () {
  await fillInquiry(this, true);
});
When("I complete the inquiry form without athlete details", async function () {
  await fillInquiry(this, false);
});
When("I review the message", async function () {
  await this.page.getByRole("button", { name: "Review my message" }).click();
});
Then("I see my message and a matching email link", async function () {
  const preview = this.page.locator("#email-preview");
  await preview.waitFor({ state: "visible" });
  const body = await this.page.locator("#email-body").textContent();
  assert.match(body, /Hi Coach Will,/);
  assert.match(body, /I’m interested in Camps\./);
  assert.match(body, /Name: Sam O’Neil & Lee\nReply email: sam@example.com/);
  assert.match(body, /Athlete: Jordan\nAge: 14/);
  assert.ok(body.includes("<script>Is Saturday available?</script>"));
  assert.equal(await this.page.locator("#email-body script").count(), 0);
  const link = new URL(
    await this.page.locator("#email-link").getAttribute("href"),
  );
  assert.equal(link.protocol, "mailto:");
  assert.equal(link.pathname, "p2vacademy@gmail.com");
  assert.equal(link.searchParams.get("subject"), "P2V inquiry: Camps");
  assert.equal(link.searchParams.get("body"), body);
  assert.equal(
    await preview.evaluate((element) => element === document.activeElement),
    true,
  );
});
When("I edit my message", async function () {
  await this.page
    .locator('[name="message"]')
    .fill("Updated availability: Sunday.");
});
Then("the email preview is hidden", async function () {
  await this.page.locator("#email-preview").waitFor({ state: "hidden" });
});
Then("I see my edited message", async function () {
  await this.page.locator("#email-preview").waitFor({ state: "visible" });
  assert.match(
    await this.page.locator("#email-body").textContent(),
    /Updated availability: Sunday\./,
  );
});
Then("the inquiry form is invalid", async function () {
  assert.equal(
    await this.page
      .locator("#inquiry")
      .evaluate((form) => form.checkValidity()),
    false,
  );
});
Then("the email preview omits athlete details", async function () {
  await this.page.locator("#email-preview").waitFor({ state: "visible" });
  const body = await this.page.locator("#email-body").textContent();
  assert.ok(!body.includes("Athlete:") && !body.includes("Age:"));
});
Given("clipboard writes {word}", async function (result) {
  await this.context.addInitScript((result) => {
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: async (text) => {
          if (result === "fail") throw new Error("Clipboard permission denied");
          window.copiedMessage = text;
        },
      },
    });
  }, result);
});
When("I copy the message", async function () {
  await this.page.getByRole("button", { name: "Copy message" }).click();
});
Then("the copy status is {string}", async function (status) {
  await this.page.waitForFunction(
    (expected) =>
      document.querySelector("#copy-status").textContent === expected,
    status,
  );
});
Then("the clipboard contains the reviewed message", async function () {
  assert.equal(
    await this.page.evaluate(() => window.copiedMessage),
    await this.page.locator("#email-body").textContent(),
  );
});
When("I expand {string}", async function (question) {
  await this.page.getByText(question, { exact: true }).click();
});
Then("I can read {string}", async function (answer) {
  await this.page
    .getByText(answer, { exact: false })
    .waitFor({ state: "visible" });
});
