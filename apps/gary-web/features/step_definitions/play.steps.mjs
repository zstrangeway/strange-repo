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
  // The one you play, unless somebody already is: a scenario saying this
  // wants a party that can play, not a statement about who controls whom.
  apiStub.addCharacterTo(world.campaign.id, {
    name,
    character_class: "rogue",
    mine: !apiStub.playedBy(world.campaign.id),
  });
});

/** Wait for the table to stop moving.
 *
 *  Arriving at a campaign with a party and nothing said begins with gary
 *  opening the scene. Waited out rather than raced: a step that started
 *  typing here would be typing into a composer gary still had. */
async function settle() {
  await world.page.waitForFunction(
    () => {
      // A campaign nobody is playing yet has no table to lay, so the page
      // sends you back to build the party. Settled there is settled.
      if (document.querySelector('[data-testid="add-character"]')) return true;
      const box = document.querySelector('[data-testid="composer"]');
      if (!box) return false;
      return (
        box.disabled === false &&
        !!document.querySelector('[data-testid="turn-gm"]')
      );
    },
    undefined,
    { timeout: 20_000 },
  );
}

When("I open that campaign", async function () {
  await world.page.goto(`${world.baseUrl}/campaigns/${world.campaign.id}`, {
    waitUntil: "domcontentloaded",
  });
  await settle();
});

When("I choose the system {string}", choose);
When("I choose the module {string}", choose);
When("I choose the model {string}", choose);

When("I name it {string} and start", async function (name) {
  await world.page.getByTestId("field-name").fill(name);
  await world.page.getByRole("button", { name: "Start the campaign" }).click();
});

async function makeCharacter(name, characterClass) {
  await world.page.getByTestId("field-character_name").fill(name);
  await world.page.getByTestId("character-class").click();
  await world.page.getByRole("option", { name: characterClass }).click();
  await world.page.getByTestId("add-character").click();
  await world.page.waitForSelector(`[data-testid="member-${name}"]`, {
    timeout: 15_000,
  });
}

// The same control either way — which of the two it is follows from who is
// already there — but a scenario saying "as mine" and a scenario saying "as a
// companion" are saying different things, and should read that way.
When("I add {string} the {string} as mine", makeCharacter);
When("I add {string} the {string} as a companion", makeCharacter);

When("I open that campaign's party", async function () {
  await world.page.goto(
    `${world.baseUrl}/campaigns/${world.campaign.id}/party`,
    { waitUntil: "domcontentloaded" },
  );
  await world.page.waitForSelector('[data-testid="add-character"]', {
    timeout: 15_000,
  });
});

When("I take them in", async function () {
  await world.page.getByTestId("take-them-in").click();
  await settle();
});

// Not "I should be on the party page": auth.steps.mjs owns
// `I should be on the (.+) page` for the fixed routes, and this one's path
// carries a campaign id that no lookup table can hold.
Then("I should be building the party", async function () {
  await world.page.waitForURL(
    (url) => /^\/campaigns\/[0-9a-f-]{36}\/party$/.test(new URL(url).pathname),
    { timeout: 15_000 },
  );
});

Then("the page should say {string} is mine", async function (name) {
  const shown = await world.page.textContent(`[data-testid="plays-${name}"]`);
  assert.match(shown ?? "", /you/i, `${name} is not shown as mine`);
});

Then("the page should say {string} is gary's", async function (name) {
  const shown = await world.page.textContent(`[data-testid="plays-${name}"]`);
  assert.match(shown ?? "", /gary/i, `${name} is not shown as gary's`);
});

Then("I should not be able to take them in", async function () {
  assert.equal(await world.page.getByTestId("take-them-in").isDisabled(), true);
});

Then("I should be able to take them in", async function () {
  await world.page.waitForFunction(
    () =>
      document.querySelector('[data-testid="take-them-in"]')?.disabled === false,
    undefined,
    { timeout: 15_000 },
  );
});

When("I say {string}", async function (message) {
  await say(message);
});

When("I say {string} and gary rolls", async function (message) {
  apiStub.garyWill({ roll: A_ROLL });
  await say(message);
});

When(
  "I say {string} and gary checks {string} on a sheet of tens",
  async function (message, who) {
    // The check every character in a new campaign actually makes: an ability
    // named, and a score of ten behind it, which is worth nothing. This is
    // what was on screen when the working went missing.
    apiStub.garyWill({
      roll: {
        notation: "1d20",
        dice: [12],
        modifier: 0,
        total: 12,
        character: who,
        ability: "dex",
        reason: "spotting the threat in the water",
        dc: 12,
        degree: "success",
      },
    });
    await say(message);
  },
);

When("I say {string} and gary checks {string}", async function (message, who) {
  // A graded check rather than a bare roll, and one with somebody's name on
  // it: the two halves of what a card has to be able to show.
  apiStub.garyWill({
    roll: {
      ...A_ROLL,
      character: who,
      ability: "dex",
      reason: "avoid collapse",
      dc: 12,
      degree: "success",
    },
  });
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

// ------------------------------------------------------------------ scenes

When("I start a new scene called {string}", async function (title) {
  await world.page.getByTestId("scene-title").fill(title);
  await world.page.getByTestId("new-scene").click();
  // Closing a scene runs a whole pass through a model, so this is the one
  // control here that is slow on purpose — wait for the seam, not the click.
  await world.page.waitForSelector('[data-testid="scene-break"]', {
    timeout: 15_000,
  });
});

When("I say {string} and gary changes scene", async function (message) {
  apiStub.garyWill({ scene: "The road to Ashfen" });
  await say(message);
});

Then("the transcript should show a break for {string}", async function (title) {
  await world.page.waitForFunction(
    (want) =>
      [...document.querySelectorAll('[data-testid="scene-title"]')].some(
        (found) => found.textContent?.trim() === want,
      ),
    title,
    { timeout: 15_000 },
  );
});

Then("the page shows what happened in the scene before", async function () {
  // The recap is now the whole of what gary remembers of that scene, so what
  // is on screen is what gary has.
  const recaps = await world.page
    .locator('[data-testid="scene-recap"]')
    .allTextContents();

  assert.ok(recaps.length > 0, "no recap was shown");
  assert.ok(recaps[0].trim().length > 0, "the recap was blank");
});

// ----------------------------------------------------------------- opening

Then("the page should not claim gary is working", async function () {
  const found = await world.page.$('[data-testid="nothing-said"]');
  const said = found ? ((await found.textContent()) ?? "") : "";
  assert.ok(
    !/setting the scene/i.test(said),
    `the page said gary was working when nobody was at the table: ${said}`,
  );
});

Then("the page should have stopped repeating the premise", async function () {
  // It earned its place while there was nothing else on screen. There is now.
  const found = await world.page.$('[data-testid="premise"]');
  assert.equal(found, null, "the premise is still on screen beside the opening");
});

Then("the page shows what the adventure is about", async function () {
  // Free and instant, so it is on screen before gary has written a word —
  // which is also what covers the seconds the opening takes to arrive.
  const shown = await world.page.textContent('[data-testid="premise"]');
  assert.ok(
    (shown ?? "").trim().length > 20,
    `no premise worth reading: ${shown}`,
  );

  // And why you are here, which is the half that was missing: without it the
  // answer to "why am I here" is only ever in gary's gift.
  const why = await world.page.textContent('[data-testid="hook"]');
  assert.ok((why ?? "").trim().length > 20, `no hook worth reading: ${why}`);
});

Then("gary should open the scene without my asking", async function () {
  // Nothing is typed and nothing is clicked between adding a character and
  // this. If it needed either, the empty box is still there.
  const answer = world.page.getByTestId("turn-gm").first();
  await answer.waitFor({ timeout: 20_000 });
  const said = (await answer.textContent()) ?? "";
  assert.ok(said.includes("marsh"), `gary opened with nothing: ${said}`);
});

Then("the composer should be waiting for me afterwards", async function () {
  await world.page.waitForFunction(
    () =>
      document.querySelector('[data-testid="composer"]')?.disabled === false,
    undefined,
    { timeout: 15_000 },
  );
});

// -------------------------------------------------------------------- rolls

Then("the roll should be labelled {string}", async function (who) {
  const shown = await world.page.textContent('[data-testid="roll-character"]');
  assert.equal(shown?.trim(), who, "the roll did not say whose it was");
});

Then("the roll should be labelled with nobody", async function () {
  // A roll about how sound the planks are belongs to nobody, and a name
  // invented to fill the space would be worse than the space.
  const found = await world.page.$('[data-testid="roll-character"]');
  assert.equal(found, null, "a roll about the world was given an owner");
});

Then("the roll should show how the total was reached", async function () {
  const shown = await world.page.textContent('[data-testid="roll-sum"]');
  // Faces, what was added, which ability it came off, and what that came to
  // — so a call this close can be checked by eye rather than taken on trust.
  assert.match(
    shown ?? "",
    /rolled \d+ [+−] \d+ \w+ = \d+/,
    shown ?? "",
  );
});

Then("the roll should say what it was against", async function () {
  const shown = await world.page.textContent('[data-testid="roll-dc"]');
  assert.match(shown ?? "", /^\d+$/, shown ?? "");
});

Then("the roll should show what the dice came up", async function () {
  // Not the arithmetic — there is none — but the faces. Without them a check
  // decided by one point is a pair of numbers you have to take on trust.
  const shown = await world.page.textContent('[data-testid="roll-sum"]');
  assert.match(shown ?? "", /rolled \d+/, shown ?? "");
});

Given("a fight is underway", async function () {
  assert.ok(world.campaign, "no campaign to fight in");
  apiStub.addCharacterTo(world.campaign.id, {
    name: "Bramble",
    character_class: "rogue",
    mine: true,
  });
  apiStub.fightUnderway(0, 1);
});

Then("{string} should be up", async function (name) {
  const shown = await world.page.textContent(`[data-testid="up-${name}"]`);
  assert.match(shown ?? "", /up/i, `${name} is not shown as up`);
});

Then("the page should say it is my turn", async function () {
  // The reason combat exists: the others are gary's to move through and it
  // stops at you. A page that did not say so would leave you waiting.
  const shown = await world.page.textContent('[data-testid="fight-yours"]');
  assert.match(shown ?? "", /your turn/i, shown ?? "");
});
