import assert from "node:assert/strict";

import { Given, When, Then } from "@cucumber/cucumber";

import * as apiStub from "../support/api-stub.mjs";
import { world } from "../support/hooks.mjs";

Given(
  "gary-api reports status {string} and database {string}",
  async function (status, database) {
    apiStub.reports(status, database);
    await apiStub.start();
  },
);

Given("gary-api is unreachable", async function () {
  await apiStub.stop();
});

When("I open the home page", async function () {
  await world.page.goto(world.baseUrl, { waitUntil: "domcontentloaded" });
});

async function expectStatus(testId, expected) {
  // Fetched in the browser after the page paints, so wait for it to settle
  // rather than reading the placeholder.
  await world.page.waitForFunction(
    ({ id, want }) =>
      document.querySelector(`[data-testid="${id}"]`)?.textContent?.trim() ===
      want,
    { id: testId, want: expected },
    { timeout: 30_000 },
  );

  const actual = await world.page.textContent(`[data-testid="${testId}"]`);
  assert.equal(actual?.trim(), expected);
}

Then("the page shows the API status {string}", async function (expected) {
  await expectStatus("api-status", expected);
});

Then("the page shows the database status {string}", async function (expected) {
  await expectStatus("database-status", expected);
});
