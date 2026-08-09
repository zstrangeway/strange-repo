import assert from "node:assert/strict";

import { Given, When, Then } from "@cucumber/cucumber";

import * as apiStub from "../support/api-stub.mjs";
import { world } from "../support/hooks.mjs";

Given("gary-api reports status {string}", async function (status) {
  assert.equal(status, "ok", "the stub only serves the healthy response");
  await apiStub.start();
});

Given("gary-api is unreachable", async function () {
  await apiStub.stop();
});

When("I open the home page", async function () {
  await world.page.goto(world.baseUrl, { waitUntil: "domcontentloaded" });
});

Then("the page shows the API status {string}", async function (expected) {
  const actual = await world.page.textContent('[data-testid="api-status"]');
  assert.equal(actual?.trim(), expected);
});
