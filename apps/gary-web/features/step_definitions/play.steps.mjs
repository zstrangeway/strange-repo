import assert from "node:assert/strict";

import { Given, When, Then } from "@cucumber/cucumber";

import * as apiStub from "../support/api-stub.mjs";
import { world, PATIENCE } from "../support/hooks.mjs";

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
 *  stub holds it — so this does not wait for the answer to finish.
 *
 *  The send is confirmed rather than assumed. The page adds the player's own
 *  entry synchronously, before the request is even made, so if the message is
 *  not on screen shortly after the click then the click did not take — and
 *  waiting the full fifteen seconds for it to appear anyway turns a lost
 *  click into a timeout that points at the wrong thing. That is what the
 *  browser tier had been failing as, in a different scenario each run.
 *
 *  A second click rather than a longer wait, because the failure is not
 *  slowness: `settle` has already waited out the opening, and the entry
 *  arrives in the same tick as the submit or not at all. */
export async function say(message) {
  world.said = message;

  const onScreen = () =>
    world.page
      .waitForFunction(
        (want) => document.body.innerText.includes(want),
        message,
        { timeout: 5_000 },
      )
      .then(
        () => true,
        () => false,
      );

  for (const attempt of [0, 1]) {
    // Enabled, not merely present: filling a composer gary still has would
    // put the message somewhere the submit will never read it.
    await composer().and(world.page.locator(":not([disabled])")).waitFor({
      state: "visible",
      timeout: PATIENCE,
    });
    await composer().fill(message);
    await world.page.getByTestId("say").click();
    if (await onScreen()) return;
    if (attempt === 1) {
      throw new Error(
        `said ${JSON.stringify(message)} twice and neither reached the screen`,
      );
    }
  }
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
    timeout: PATIENCE,
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
    timeout: PATIENCE,
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
    { timeout: PATIENCE },
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
    { timeout: PATIENCE },
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
    { timeout: PATIENCE },
  );
});

When("I move it to {string}", async function (name) {
  await world.page.getByTestId("model").click();
  await world.page.getByRole("menuitem", { name: new RegExp(name) }).click();
});

Then("there should be a way to start one", async function () {
  await world.page.waitForSelector('a[href="/campaigns/new"]', {
    timeout: PATIENCE,
  });
});

Then("I should be on a campaign page", async function () {
  await world.page.waitForURL(
    (url) => /^\/campaigns\/[0-9a-f-]{36}$/.test(new URL(url).pathname),
    { timeout: PATIENCE },
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
    { timeout: PATIENCE },
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
  await answer.waitFor({ timeout: PATIENCE });
  const said = (await answer.textContent()) ?? "";
  assert.ok(said.trim().length > "gary".length, "gary said nothing");
});

Then(
  "the narration should appear while it is still being written",
  async function () {
    const answer = world.page.getByTestId("turn-gm").last();
    await answer.waitFor({ timeout: PATIENCE });
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
    timeout: PATIENCE,
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
    { timeout: PATIENCE },
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
    { timeout: PATIENCE },
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

// ------------------------------------------------------------- creation

Given('I already have a campaign on {string}', async function (system) {
  const account = apiStub.onlyAccount();
  assert.ok(account, "no account to hang a campaign on — sign in first");
  world.campaign = apiStub.addCampaign(account.id, {
    name: "Salt in the wind",
    system,
    // The system's own first module rather than a slug written here: every
    // system has one, and naming another system's would arrange a campaign
    // gary-api would never hand back.
    module: apiStub.firstModuleOf(system),
  });
});

Then("I should be able to choose how scores are decided", async function () {
  await world.page.waitForSelector('[data-testid="method"]', { timeout: PATIENCE });
});

Then("the choices should be the system's own", async function () {
  // Never a list this app keeps. A second place for the rules to live is the
  // first place for them to go stale, so what is offered is compared against
  // what the catalogue said rather than against anything written here.
  await world.page.getByTestId("method").click();
  const offered = await world.page.getByRole("option").allTextContents();
  const answered = await world.page.evaluate(async (base) => {
    const response = await fetch(`${base}/catalogue/dnd-5e`);
    return (await response.json()).methods.map((one) => one.name);
  }, world.apiUrl);

  assert.deepEqual(offered.map((one) => one.trim()), answered);
  await world.page.keyboard.press("Escape");
});

When("I choose {string}", async function (label) {
  // A different method produces a different set, and the old one is not the
  // one anything after this has to still hold.
  world.setWas = null;
  await world.page.getByTestId("method").click();
  await world.page.getByRole("option", { name: label, exact: false }).click();
});

/**
 * What is against each ability, read off whichever control is holding it.
 *
 * A chip that was dragged there, a number between two steppers and a typed box
 * are three controls and one question, so they all answer it the same way:
 * which ability, and what it currently says.
 */
async function sheetNow() {
  return await world.page.$$eval('[data-testid="sheet"] [data-ability]', (nodes) =>
    Object.fromEntries(
      nodes.map((one) => [one.dataset.ability, one.dataset.score ?? one.value ?? ""]),
    ),
  );
}

/** Everything the roll produced, wherever it currently sits. */
async function rolledNow() {
  return (await rolledSet()).join("|");
}

/** Remember the sheet, so a step after this one can say what moved.
 *
 *  And the set itself, the first time anything is moved since it arrived: what
 *  the method produced is what the sheet has to still hold afterwards, however
 *  much it is rearranged. */
async function remember() {
  world.sheetWas = await sheetNow();
  if (!world.setWas) world.setWas = await rolledSet();
}

/** Roll, and wait for a set that is not the one already on screen. */
async function rollScores() {
  world.setWas = null;
  world.wasRolled = await rolledNow();
  await world.page.getByTestId("roll-scores").click();
  await world.page.waitForFunction(
    (before) => {
      const shown = [
        ...document.querySelectorAll('[data-testid="sheet"] [data-ability]'),
      ]
        .map((one) => one.dataset.score ?? one.value ?? "")
        .join("|");
      return shown.length > 0 && !shown.includes("undefined") && shown !== before;
    },
    world.wasRolled,
    { timeout: PATIENCE },
  );
}

When("I roll for scores", rollScores);
When("I roll for scores again", rollScores);

Then("the scores should have changed", async function () {
  assert.notEqual(await rolledNow(), world.wasRolled, "the same set twice");
});

Then("there should be nothing to roll", async function () {
  const found = await world.page.$('[data-testid="roll-scores"]');
  assert.equal(found, null, "a method that generates nothing offered a roll");
});

// ------------------------------------------------- rolled, and yours to place

Then("every ability should hold one of the rolled scores", async function () {
  await world.page.waitForFunction(
    () => {
      const held = [
        ...document.querySelectorAll('[data-testid="sheet"] [data-ability]'),
      ];
      return held.length > 0 && held.every((one) => /^\d+$/.test(one.dataset.score ?? ""));
    },
    null,
    { timeout: PATIENCE },
  );
});

Then("there should be nothing to type", async function () {
  // The whole complaint, in one assertion: the numbers are on the screen
  // already and nobody should be transcribing them.
  const boxes = await world.page.locator('[data-testid="sheet"] input').count();
  assert.equal(boxes, 0, "the sheet still asked for the numbers to be typed");
});

Then("there should be nothing to choose", async function () {
  // A method that arranges nothing offers no choosers and no boxes: every
  // control on the sheet is a button of one kind or another, so counting
  // buttons counts them all.
  const controls = await world.page
    .locator('[data-testid="sheet"] button')
    .count();
  assert.equal(controls, 0, "a method that arranges nothing offered a choice");
});

Then("every ability should say what its score is worth", async function () {
  const shown = await world.page
    .locator('[data-testid="sheet"] [data-ability]')
    .allTextContents();
  assert.ok(shown.length > 0, "there was no sheet");
  for (const one of shown) {
    assert.match(one, /\(\s*[+-]\d+\s*\)/, `no modifier beside ${one}`);
  }
});

Then("no score should say it is worth anything", async function () {
  // First edition has a table per ability and no general modifier, which
  // gary-api answers with nothing rather than by halving the distance from
  // ten. A page showing "(+0)" would be inventing an answer it was not given.
  const shown = await world.page
    .locator('[data-testid="sheet"] [data-ability]')
    .allTextContents();
  assert.ok(shown.length > 0, "there was no sheet");
  for (const one of shown) {
    assert.doesNotMatch(one, /\([+-]/, `${one} claimed to be worth something`);
  }
});

/** The abilities in the order the sheet lists them. */
async function sheetOrder() {
  return await world.page.$$eval(
    '[data-testid="sheet"] [data-ability]',
    (nodes) => nodes.map((one) => one.dataset.ability),
  );
}

/** Open one ability's chooser and take the option at a position in the set. */
async function give(ability, at) {
  await world.page.getByTestId(`score-${ability}`).click();
  await world.page.getByRole("option").nth(at).click();
  // The trigger closing is the page having taken it.
  await world.page.getByRole("option").first().waitFor({ state: "detached" });
}

/** Where in the rolled set the score on an ability came from.
 *
 *  A position and never a value: two dice can come to the same total, and
 *  "the 13" cannot say which 13 was moved. */
async function heldAt(ability) {
  return Number(
    await world.page
      .getByTestId(`score-${ability}`)
      .evaluate((node) => node.getAttribute("data-held")),
  );
}

When(
  "I give {string} the score that was on {string}",
  async function (ability, from) {
    await remember();
    await give(ability, await heldAt(from));
  },
);

Then("{string} and {string} should have swapped", async function (one, two) {
  const now = await sheetNow();
  assert.equal(now[one], world.sheetWas[two], `${one} did not take ${two}'s`);
  assert.equal(now[two], world.sheetWas[one], `${two} did not take ${one}'s`);
});

Then("each ability should offer every rolled score", async function () {
  // Including the ones already somewhere: taking one of those is how two are
  // swapped, and leaving them out would leave no way to.
  const wanted = (await rolledSet()).length;
  for (const ability of await sheetOrder()) {
    await world.page.getByTestId(`score-${ability}`).click();
    const offered = await world.page.getByRole("option").count();
    assert.equal(offered, wanted, `${ability} offered ${offered} of ${wanted}`);
    await world.page.keyboard.press("Escape");
    await world.page.getByRole("option").first().waitFor({ state: "detached" });
  }
});

/** Every score the method produced, wherever it currently sits. */
async function rolledSet() {
  const sheet = Object.values(await sheetNow());
  return [...sheet, ...(await spareNow())].sort();
}

Then("the sheet should still hold the whole rolled set", async function () {
  // None taken twice and none lost. Compared against what was on screen when
  // the set arrived, because the set is the method's and arranging is only
  // arranging.
  assert.deepEqual(await rolledSet(), world.setWas, "the set changed");
});

Then("there should be scores going spare", async function () {
  assert.ok((await spareNow()).length > 0, "the spare scores went nowhere");
});

Then("there should be nothing going spare", async function () {
  assert.deepEqual(await spareNow(), [], "scores were left over");
});

/** What nothing is holding, as the page lists it. */
async function spareNow() {
  const shown = await world.page.$('[data-testid="spare"]');
  if (!shown) return [];
  const text = (await shown.textContent()) ?? "";
  return (text.match(/\b\d+\b(?=\s*\()/g) ?? []).sort();
}

When("I give {string} a score that was going spare", async function (ability) {
  await remember();
  world.displaced = world.sheetWas[ability];
  // A spare one is a position on the chooser that nothing on the sheet is
  // holding. Found by position rather than by reading the spare list, which is
  // a set of numbers and cannot say which of two equal ones is meant.
  const held = await Promise.all(
    (await sheetOrder()).map((one) => heldAt(one)),
  );
  const size = (await rolledSet()).length;
  const free = [...Array(size).keys()].filter((at) => !held.includes(at));
  assert.ok(free.length > 0, "nothing was going spare");

  await world.page.getByTestId(`score-${ability}`).click();
  const taking = world.page.getByRole("option").nth(free[0]);
  // What that one reads as, so the step after this can say it arrived.
  world.wasSpare = ((await taking.textContent()) ?? "").match(/\d+/)[0];
  await taking.click();
  await world.page.getByRole("option").first().waitFor({ state: "detached" });
});

Then("{string} should hold that score", async function (ability) {
  const now = await sheetNow();
  assert.equal(now[ability], world.wasSpare, `${ability} holds ${now[ability]}`);
});

Then("the score it displaced should be going spare", async function () {
  const spare = await spareNow();
  assert.ok(
    spare.includes(world.displaced),
    `${world.displaced} was displaced but is not spare: ${spare.join(", ")}`,
  );
});

// ---------------------------------------------------------------- point buy

/** The table's ends, as the page itself states them. Read rather than written
 *  here, because what a system prices is the system's. */
async function tableEnds() {
  const shown = await world.page.textContent('[data-testid="point-spend"]');
  const found = shown.match(/(\d+) to (\d+) each/);
  assert.ok(found, `the page did not say what the table prices: ${shown}`);
  return [Number(found[1]), Number(found[2])];
}

async function spendNow() {
  const shown = await world.page.textContent('[data-testid="point-spend"]');
  const found = shown.match(/(\d+) of (\d+)/);
  assert.ok(found, `the page did not say what has been spent: ${shown}`);
  return [Number(found[1]), Number(found[2])];
}

Then(
  "every ability should start at the cheapest score the table prices",
  async function () {
    const [cheapest] = await tableEnds();
    const sheet = await sheetNow();
    assert.ok(Object.keys(sheet).length > 0, "there was no sheet");
    for (const [ability, score] of Object.entries(sheet)) {
      assert.equal(Number(score), cheapest, `${ability} started at ${score}`);
    }
  },
);

Then("nothing should be spent yet", async function () {
  const [paid] = await spendNow();
  assert.equal(paid, 0, `${paid} was already spent`);
});

When("I raise {string} {int} times", async function (ability, times) {
  for (let each = 0; each < times; each += 1) {
    await world.page.getByTestId(`raise-${ability}`).click();
  }
});

Then("{string} should read {int}", async function (ability, score) {
  const sheet = await sheetNow();
  assert.equal(Number(sheet[ability]), score, `${ability} reads ${sheet[ability]}`);
});

Then("the spend should be {int} of {int}", async function (paid, budget) {
  assert.deepEqual(await spendNow(), [paid, budget]);
});

When(
  "I raise every ability as far as the page will let me",
  async function () {
    world.spends = [];
    for (const ability of await sheetOrder()) {
      // Bounded, so a stepper that never disables fails as a hang rather than
      // spinning: no table is longer than the scores a system allows.
      for (let each = 0; each < 40; each += 1) {
        const arrow = world.page.getByTestId(`raise-${ability}`);
        if (await arrow.isDisabled()) break;
        await arrow.click();
        world.spends.push((await spendNow())[0]);
      }
    }
  },
);

Then("the spend should never have gone over {int}", async function (budget) {
  const over = (world.spends ?? []).filter((one) => one > budget);
  assert.deepEqual(over, [], `the budget was exceeded: ${over.join(", ")}`);
});

Then("I should not be able to raise {string}", async function (ability) {
  assert.equal(
    await world.page.getByTestId(`raise-${ability}`).isDisabled(),
    true,
    `${ability} could still be raised`,
  );
});

Then("I should not be able to lower {string}", async function (ability) {
  assert.equal(
    await world.page.getByTestId(`lower-${ability}`).isDisabled(),
    true,
    `${ability} could still be lowered`,
  );
});

When("I raise {string} to the top of the table", async function (ability) {
  const [, top] = await tableEnds();
  for (let each = 0; each < 40; each += 1) {
    const sheet = await sheetNow();
    if (Number(sheet[ability]) === top) return;
    await world.page.getByTestId(`raise-${ability}`).click();
  }
  assert.fail(`${ability} never reached ${top}`);
});

// ------------------------------------------------------------------- typing

Then("I should be able to type each score", async function () {
  for (const ability of await sheetOrder()) {
    assert.equal(
      await world.page.getByTestId(`score-${ability}`).isEditable(),
      true,
      `${ability} was not typeable`,
    );
  }
});

When("I type {int} for {string}", async function (score, ability) {
  await world.page.getByTestId(`score-${ability}`).fill(String(score));
});

When(
  "I type {int} for {string} and add {string} the {string} as mine",
  async function (score, ability, name, characterClass) {
    await world.page.getByTestId(`score-${ability}`).fill(String(score));
    await world.page.getByTestId("field-character_name").fill(name);
    await world.page.getByTestId("character-class").click();
    await world.page.getByRole("option", { name: characterClass }).click();
    await world.page.getByTestId("add-character").click();
  },
);

// ------------------------------------------------------------------ the party

Then("the party should show what {word} is made of", async function (name) {
  const shown = await world.page.textContent(`[data-testid="member-${name}"]`);
  assert.match(shown ?? "", /\d+\/\d+/, shown ?? "");
});

Then("the party should not show {string}", async function (what) {
  const shown = await world.page.textContent('[data-testid="party"]');
  assert.ok(!shown?.includes(what), `the party still shows ${what}`);
});

Then(
  "the page should say scores cannot be generated for this system",
  async function () {
    const shown = await world.page.textContent(
      '[data-testid="cannot-generate"]',
    );
    assert.ok((shown ?? "").trim().length > 20, shown ?? "");
  },
);

Then("I should be able to choose {string}", async function (label) {
  await world.page.getByTestId("method").click();
  await world.page
    .getByRole("option", { name: label, exact: false })
    .waitFor({ timeout: PATIENCE });
  await world.page.keyboard.press("Escape");
});

Then(
  "I should still be able to add {string} the {string} as mine",
  async function (name, characterClass) {
    await makeCharacter(name, characterClass);
  },
);
