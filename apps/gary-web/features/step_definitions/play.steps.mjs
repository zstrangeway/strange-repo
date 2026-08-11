import assert from "node:assert/strict";

import { Given, When, Then } from "@cucumber/cucumber";

import * as apiStub from "../support/api-stub.mjs";
import { world } from "../support/hooks.mjs";

// The table, in a browser.
//
// gary-api's own specs prove the frames are sent and the engines decide; what
// these prove is that a browser renders a turn as it arrives rather than all
// at once at the end. That distinction is the reason the stub holds every
// stream open until a step says otherwise — a turn that ended the moment it
// began could not be looked at mid-flight, which is the only place streaming
// is distinguishable from not streaming.

const A_ROLL = {
  notation: "1d20+3",
  dice: [14],
  modifier: 3,
  total: 17,
  reason: "Perception",
};

function composer() {
  return world.page.getByTestId("composer");
}

/** Click something offered by its accessible name, which is the name a
 *  person reads off the screen. */
async function choose(label) {
  await world.page.getByRole("button", { name: label, exact: true }).click();
}

/** Type into the composer and send it. The turn stays open afterwards — the
 *  stub holds it — so this does not wait for the answer to finish. */
async function say(message) {
  world.said = message;
  await composer().fill(message);
  await world.page.getByTestId("say").click();
  // The player's turn is on screen before gary has said anything, which is
  // what makes it safe to assert on it while gary is still writing.
  await world.page.waitForFunction(
    (want) => document.body.innerText.includes(want),
    message,
    { timeout: 15_000 },
  );
}

Given("I already have a campaign called {string}", async function (name) {
  const account = apiStub.onlyAccount();
  assert.ok(account, "no account to hang a campaign on — sign in first");
  world.campaign = apiStub.addCampaign(account.id, { name });
});

Given("{string} the rogue is at the table", async function (name) {
  assert.ok(world.campaign, "no campaign to put anybody in");
  apiStub.addCharacterTo(world.campaign.id, {
    name,
    character_class: "rogue",
  });
});

When("I open that campaign", async function () {
  await world.page.goto(`${world.baseUrl}/campaigns/${world.campaign.id}`, {
    waitUntil: "domcontentloaded",
  });
  await world.page.waitForSelector('[data-testid="composer"]', {
    timeout: 15_000,
  });
});

When("I choose the system {string}", choose);
When("I choose the module {string}", choose);
When("I choose the model {string}", choose);

When("I name it {string} and start", async function (name) {
  await world.page.getByTestId("field-name").fill(name);
  await world.page.getByRole("button", { name: "Start the campaign" }).click();
});

When("I add {string} the {string}", async function (name, characterClass) {
  await world.page.getByTestId("field-character_name").fill(name);
  await world.page.getByTestId("character-class").click();
  await world.page.getByRole("option", { name: characterClass }).click();
  await world.page.getByTestId("add-character").click();
});

When("I say {string}", async function (message) {
  await say(message);
});

When("I say {string} and gary rolls", async function (message) {
  apiStub.garyWill({ roll: A_ROLL });
  await say(message);
});

When("I say {string} and gary falls over", async function (message) {
  apiStub.garyWill({ fail: "gary is unavailable, try again shortly" });
  await say(message);
});

When("I say {string} and gary declines", async function (message) {
  apiStub.garyWill({ refuse: "I would rather not narrate that" });
  await say(message);
});

When("gary finishes", async function () {
  apiStub.garyFinishes();
  // The composer coming back is how the page says the turn is over, so it is
  // also how this step knows the frame arrived rather than merely being sent.
  await world.page.waitForFunction(
    () =>
      document.querySelector('[data-testid="composer"]')?.disabled === false,
    undefined,
    { timeout: 15_000 },
  );
});

When("I move it to {string}", async function (name) {
  await world.page.getByTestId("model").click();
  await world.page.getByRole("menuitem", { name: new RegExp(name) }).click();
});

Then("there should be a way to start one", async function () {
  await world.page.waitForSelector('a[href="/campaigns/new"]', {
    timeout: 15_000,
  });
});

Then("I should be on a campaign page", async function () {
  await world.page.waitForURL(
    (url) => /^\/campaigns\/[0-9a-f-]{36}$/.test(new URL(url).pathname),
    { timeout: 15_000 },
  );
});

Then("each model should show its price", async function () {
  const prices = await world.page
    .locator('[data-testid="model-price"]')
    .allTextContents();

  assert.ok(prices.length > 0, "no models were offered");
  for (const price of prices) {
    // The whole point of exposing the choice is that the numbers differ
    // enormously, so a name without a number beside it is the choice given
    // away again.
    assert.match(price, /\$\d/, `a model showed no price: ${price}`);
  }
});

Then("I should not be able to say anything", async function () {
  assert.equal(await composer().isDisabled(), true);
});

Then(
  "I should not be able to say anything while gary is answering",
  async function () {
    // Not politeness: a second turn sent mid-stream would be narrated against
    // a transcript that does not yet hold the first one.
    assert.equal(await composer().isDisabled(), true);
  },
);

Then("I should be able to say something again", async function () {
  await world.page.waitForFunction(
    () =>
      document.querySelector('[data-testid="composer"]')?.disabled === false,
    undefined,
    { timeout: 15_000 },
  );
});

Then("the transcript should show what I said", async function () {
  const shown = await world.page.textContent('[data-testid="transcript"]');
  assert.ok(
    shown?.includes(world.said),
    `the transcript did not hold "${world.said}"`,
  );
});

Then("the transcript should still show what I said", async function () {
  // The same assertion, after something went wrong. A turn that vanishes
  // when gary fails leaves the next one being told a story that never
  // happened.
  const shown = await world.page.textContent('[data-testid="transcript"]');
  assert.ok(
    shown?.includes(world.said),
    `the transcript lost "${world.said}"`,
  );
});

Then("gary should answer", async function () {
  const answer = world.page.getByTestId("turn-gm").last();
  await answer.waitFor({ timeout: 15_000 });
  const said = (await answer.textContent()) ?? "";
  assert.ok(said.trim().length > "gary".length, "gary said nothing");
});

Then(
  "the narration should appear while it is still being written",
  async function () {
    const answer = world.page.getByTestId("turn-gm").last();
    await answer.waitFor({ timeout: 15_000 });
    const said = (await answer.textContent()) ?? "";

    // Both halves matter. Narration on screen proves it rendered; the
    // composer still disabled proves the turn had not finished when it did.
    assert.ok(said.includes("groans"), `nothing was narrated yet: ${said}`);
    assert.equal(
      await composer().isDisabled(),
      true,
      "the turn was already over, so this proves nothing",
    );
  },
);

Then("the transcript should show a roll of {string}", async function (notation) {
  const shown = await world.page.textContent('[data-testid="roll-notation"]');
  assert.equal(shown?.trim(), notation);
});

Then("the roll should show its total", async function () {
  const total = await world.page.textContent('[data-testid="roll-total"]');
  assert.match(total?.trim() ?? "", /^\d+$/);
});

Then("the page shows an error about gary", async function () {
  // It has to read as gary having a problem rather than as the page being
  // broken: what went wrong arrived on an open stream, and the transcript
  // around it is still good.
  const shown = (await world.page.textContent('[data-testid="error"]')) ?? "";
  assert.match(shown, /gary/i);
});

Then("the page shows that gary declined", async function () {
  const shown = (await world.page.textContent('[data-testid="error"]')) ?? "";
  assert.match(shown, /declined/i);
});

Then("the page shows which model is running it", async function () {
  const shown = (await world.page.textContent('[data-testid="model"]')) ?? "";
  assert.ok(shown.trim().length > 0, "no model was named");
});
