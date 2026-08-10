import assert from "node:assert/strict";

import { Given, When, Then } from "@cucumber/cucumber";

import * as apiStub from "../support/api-stub.mjs";
import { world } from "../support/hooks.mjs";

const PAGES = {
  home: "/",
  "sign in": "/login",
  profile: "/profile",
};

function pathFor(name) {
  const found = PAGES[name.trim()];
  if (!found) {
    throw new Error(`no page called "${name}" — add it to PAGES`);
  }
  return found;
}

async function open(path) {
  await world.page.goto(`${world.baseUrl}${path}`, {
    waitUntil: "domcontentloaded",
  });
}

function path() {
  return new URL(world.page.url()).pathname;
}

/** Press a provider button and wait out the trip through it and back. */
async function through(provider, testId) {
  await Promise.all([
    world.page.waitForLoadState("networkidle"),
    world.page.click(`[data-testid="${testId}-${provider}"]`),
  ]);
}

Given("I am signed out", async function () {
  await world.page.context().clearCookies();
});

Given("I have never signed in", async function () {
  await world.page.context().clearCookies();
});

Given(
  '{word} will say I am "{}" named "{}"',
  async function (provider, email, name) {
    apiStub.nextPerson(provider, { email, name });
  },
);

Given("{word} will not say who I am", async function (provider) {
  // Arranging nobody is how the stub produces a provider that refuses.
});

Given("only {word} and {word} are offered", async function (first, second) {
  apiStub.onlyProviders([first, second]);
});

Given(
  'an account already exists at {word} for "{}" named "{}"',
  async function (provider, email, name) {
    apiStub.addAccount(provider, { email, name });
  },
);

Given(
  'I have signed in at {word} as "{}" named "{}"',
  async function (provider, email, name) {
    apiStub.nextPerson(provider, { email, name });
    await open("/login");
    await through(provider, "sign-in");
    await world.page.waitForSelector('[data-testid="welcome"]', {
      timeout: 15_000,
    });
  },
);

When("I sign in with {word}", async function (provider) {
  if (path() !== "/login") {
    await open("/login");
  }
  await through(provider, "sign-in");
});

When("I connect {word}", async function (provider) {
  if (path() !== "/profile") {
    await open("/profile");
  }
  await through(provider, "connect");
});

When("I disconnect {word}", async function (provider) {
  await Promise.all([
    world.page.waitForLoadState("networkidle"),
    world.page.click(`[data-testid="disconnect-${provider}"]`),
  ]);
});

When(/^I open the (.+) page$/, async function (name) {
  await open(pathFor(name));
});

When("I reload the page", async function () {
  await world.page.reload({ waitUntil: "domcontentloaded" });
});

When("I sign out", async function () {
  await world.page.getByTestId("user-menu").click();
  await Promise.all([
    world.page.waitForLoadState("networkidle"),
    world.page.getByRole("menuitem", { name: "Sign out" }).click(),
  ]);
});

When("I change my display name to {string}", async function (name) {
  await world.page.fill('[data-testid="field-display_name"]', name);
  await Promise.all([
    world.page.waitForLoadState("networkidle"),
    world.page.getByRole("button", { name: "Save name" }).click(),
  ]);
});

Then("the page shows {string}", async function (expected) {
  await world.page.waitForFunction(
    (want) => document.body.innerText.includes(want),
    expected,
    { timeout: 15_000 },
  );
});

Then("the welcome does not show {string}", async function (unwanted) {
  const welcome = (await world.page.textContent('[data-testid="welcome"]')) ?? "";
  assert.ok(!welcome.includes(unwanted), `the welcome showed ${unwanted}`);
});

Then(/^I should be on the (.+) page$/, async function (name) {
  const expected = pathFor(name);
  await world.page.waitForURL((url) => new URL(url).pathname === expected, {
    timeout: 15_000,
  });
  assert.equal(path(), expected);
});

Then("the page shows an error {string}", async function (expected) {
  const actual = await world.page.textContent('[data-testid="error"]');
  assert.equal(actual?.trim(), expected);
});

Then(/^the page shows an error about the (.+)$/, async function (subject) {
  const actual = (await world.page.textContent('[data-testid="error"]')) ?? "";
  const keyword = subject.split(" ")[0].toLowerCase();
  assert.ok(
    actual.toLowerCase().includes(keyword),
    `error did not mention ${keyword}: ${actual}`,
  );
});

Then("the page shows a confirmation", async function () {
  await world.page.waitForSelector('[data-testid="confirmation"]', {
    timeout: 15_000,
  });
});

Then("the page shows no error", async function () {
  const found = await world.page.$('[data-testid="error"]');
  assert.equal(found, null, "an error was showing");
});

Then('the page shows my email {string}', async function (email) {
  const actual = await world.page.textContent('[data-testid="profile-email"]');
  assert.equal(actual?.trim(), email);
});

Then('the page shows my display name {string}', async function (name) {
  const actual = await world.page.inputValue('[data-testid="field-display_name"]');
  assert.equal(actual, name);
});

Then("{word} should be offered", async function (provider) {
  await world.page.waitForSelector(`[data-testid="sign-in-${provider}"]`);
});

Then("{word} should not be offered", async function (provider) {
  const found = await world.page.$(`[data-testid="sign-in-${provider}"]`);
  assert.equal(found, null, `${provider} was offered and should not be`);
});

Then("{word} should be connected", async function (provider) {
  const text = await world.page.textContent(
    `[data-testid="connection-${provider}"]`,
  );
  assert.ok(
    !text.includes("Not connected"),
    `${provider} reads as not connected: ${text}`,
  );
});

Then("{word} should not be connected", async function (provider) {
  const text = await world.page.textContent(
    `[data-testid="connection-${provider}"]`,
  );
  assert.ok(
    text.includes("Not connected"),
    `${provider} reads as connected: ${text}`,
  );
});

Then("I cannot disconnect {word}", async function (provider) {
  const disabled = await world.page.getAttribute(
    `[data-testid="disconnect-${provider}"]`,
    "disabled",
  );
  assert.notEqual(disabled, null, `${provider} could still be disconnected`);
});
