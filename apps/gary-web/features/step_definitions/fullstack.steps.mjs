import { When } from "@cucumber/cucumber";

import { world } from "../support/hooks.mjs";

// gary-api's own stand-in provider shows a consent page rather than bouncing
// straight back, because a real provider does. These steps agree at it the
// way a person would: say who you are, press the button.
async function agreeAs(identity) {
  await world.page.waitForSelector('[data-testid="fake-identity"]', {
    timeout: 15_000,
  });
  await world.page.fill('[data-testid="fake-identity"]', identity);
  await Promise.all([
    world.page.waitForLoadState("networkidle"),
    world.page.click('[data-testid="fake-continue"]'),
  ]);
}

When(
  'I sign in with {word}, agreeing as {string}',
  async function (provider, identity) {
    await Promise.all([
      world.page.waitForLoadState("domcontentloaded"),
      world.page.click(`[data-testid="sign-in-${provider}"]`),
    ]);
    await agreeAs(identity);
  },
);

When(
  'I connect {word}, agreeing as {string}',
  async function (provider, identity) {
    await Promise.all([
      world.page.waitForLoadState("domcontentloaded"),
      world.page.click(`[data-testid="connect-${provider}"]`),
    ]);
    await agreeAs(identity);
  },
);
