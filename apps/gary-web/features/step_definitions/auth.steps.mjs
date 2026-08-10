import assert from "node:assert/strict";

import { Given, When, Then } from "@cucumber/cucumber";

import * as apiStub from "../support/api-stub.mjs";
import { world } from "../support/hooks.mjs";

const PASSWORD = "a long enough password";

const PAGES = {
  home: "/",
  "sign in": "/login",
  "sign up": "/signup",
  profile: "/profile",
  "password reset": "/forgot",
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

async function fill(name, value) {
  await world.page.fill(`[data-testid="field-${name}"]`, value);
}

async function submit(label) {
  await Promise.all([
    world.page.waitForLoadState("networkidle"),
    world.page.getByRole("button", { name: label }).click(),
  ]);
}

function path() {
  return new URL(world.page.url()).pathname;
}

Given("I am signed out", async function () {
  await world.page.context().clearCookies();
});

Given("an account already exists for {string}", async function (email) {
  apiStub.addUser(email, "Ada", PASSWORD);
});

Given(
  'an account already exists for {string} with name {string} and password {string}',
  async function (email, name, password) {
    apiStub.addUser(email, name, password);
  },
);

Given("I am signed in as {string}", async function (name) {
  // Only create it if the scenario has not already set one up — otherwise
  // this quietly undoes arrangements like "has verified their address".
  if (!apiStub.hasUser("ada@example.com")) {
    apiStub.addUser("ada@example.com", name, PASSWORD);
  }
  await open("/login");
  await fill("email", "ada@example.com");
  await fill("password", PASSWORD);
  await submit("Sign in");
});

Given(
  "I am signed in as {string} with email {string}",
  async function (name, email) {
    if (!apiStub.hasUser(email)) {
      apiStub.addUser(email, name, PASSWORD);
    }
    await open("/login");
    await fill("email", email);
    await fill("password", PASSWORD);
    await submit("Sign in");
  },
);

Given("gary-api is unreachable", async function () {
  await apiStub.stop();
});

Given("{string} has been sent a reset link", async function (email) {
  await open("/forgot");
  await fill("email", email);
  await submit("Send me a link");
  world.resetToken = apiStub.lastResetToken();
  assert.ok(world.resetToken, "no reset link was issued");
});

Given(
  'the link has already been used to set the password {string}',
  async function (password) {
    apiStub.markResetUsed(world.resetToken, password);
  },
);

Given("the link expired an hour ago", async function () {
  apiStub.expireReset(world.resetToken);
});

When(/^I open the (.+) page$/, async function (name) {
  await open(pathFor(name));
});

When("I reload the page", async function () {
  await world.page.reload({ waitUntil: "domcontentloaded" });
});

When("I open the reset link", async function () {
  await open(`/reset?token=${encodeURIComponent(world.resetToken)}`);
});

When(
  'I sign up as {string} with email {string} and password {string}',
  async function (name, email, password) {
    await fill("display_name", name);
    await fill("email", email);
    await fill("password", password);
    await submit("Sign up");
  },
);

When(
  'I sign in with email {string} and password {string}',
  async function (email, password) {
    if (path() !== "/login") {
      await open("/login");
    }
    await fill("email", email);
    await fill("password", password);
    await submit("Sign in");
  },
);

When("I sign out", async function () {
  // Sign out moved into the sidebar's user menu when gary-web grew a real
  // app layout, so it takes opening the menu first.
  await world.page.getByTestId("user-menu").click();
  await Promise.all([
    world.page.waitForLoadState("networkidle"),
    world.page.getByRole("menuitem", { name: "Sign out" }).click(),
  ]);
});

When("I follow {string}", async function (label) {
  await Promise.all([
    world.page.waitForLoadState("domcontentloaded"),
    world.page.getByRole("link", { name: label }).click(),
  ]);
});

When('I ask for a reset link for {string}', async function (email) {
  await fill("email", email);
  await submit("Send me a link");
});

When('I change my display name to {string}', async function (name) {
  await fill("display_name", name);
  await submit("Save name");
});

When(
  'I change my password from {string} to {string}',
  async function (current, next) {
    await fill("current_password", current);
    await fill("new_password", next);
    await submit("Change password");
  },
);

When('I set my new password to {string}', async function (password) {
  await fill("new_password", password);
  await submit("Set password");
});

Then("the page shows {string}", async function (expected) {
  await world.page.waitForFunction(
    (want) => document.body.innerText.includes(want),
    expected,
    { timeout: 15_000 },
  );
});

Then("the page does not show {string}", async function (unwanted) {
  const body = await world.page.innerText("body");
  assert.ok(!body.includes(unwanted), `page showed ${unwanted}`);
});

Then("the welcome does not show {string}", async function (unwanted) {
  const welcome = (await world.page.textContent('[data-testid="welcome"]')) ?? "";
  assert.ok(!welcome.includes(unwanted), `the welcome showed ${unwanted}`);
});

Then(/^I should be on the (.+) page$/, async function (name) {
  const expected = pathFor(name);
  // Compared on pathname: /login?reset=1 is still the sign in page.
  await world.page.waitForURL((url) => new URL(url).pathname === expected, {
    timeout: 15_000,
  });
  assert.equal(path(), expected);
});

Then(/^I should still be on the (.+) page$/, async function (name) {
  assert.equal(path(), pathFor(name));
});

Then("the page shows an error {string}", async function (expected) {
  const actual = await world.page.textContent('[data-testid="error"]');
  assert.equal(actual?.trim(), expected);
});

Then(/^the page shows an error about the (.+)$/, async function (subject) {
  const actual = (await world.page.textContent('[data-testid="error"]')) ?? "";
  // "password length" and "email address" both key off their first word.
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

Then('the page shows my email {string}', async function (email) {
  const actual = await world.page.textContent('[data-testid="profile-email"]');
  assert.equal(actual?.trim(), email);
});

Then('the page shows my display name {string}', async function (name) {
  const actual = await world.page.inputValue('[data-testid="field-display_name"]');
  assert.equal(actual, name);
});

Given("{string} has verified their address", async function (email) {
  apiStub.verifyUser(email);
});

function verificationToken() {
  // Remembered on first use. lastVerificationToken() only reports live
  // tokens, so a scenario that spends one would find nothing left to open —
  // which is exactly what the used-link and expired-link cases do.
  world.verificationToken ??= apiStub.lastVerificationToken();
  assert.ok(world.verificationToken, "no verification link was issued");
  return world.verificationToken;
}

Given("the verification link has already been used", async function () {
  apiStub.markVerificationUsed(verificationToken());
});

Given("the verification link expired a day ago", async function () {
  apiStub.expireVerification(verificationToken());
});

When("I open the verification link", async function () {
  await open(`/verify?token=${encodeURIComponent(verificationToken())}`);
});

Then("the page shows an unverified notice", async function () {
  await world.page.waitForSelector('[data-testid="unverified"]', {
    timeout: 15_000,
  });
});

Then("the page does not show an unverified notice", async function () {
  const found = await world.page.$('[data-testid="unverified"]');
  assert.equal(found, null, "the unverified notice was still showing");
});

When("I press {string}", async function (label) {
  await submit(label);
});
