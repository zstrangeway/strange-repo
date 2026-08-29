// Advancement on the table: what a card says, and what a turn shows.
//
// The card's numbers come from the world and the transcript's lines come from
// the stream, which is the split these scenarios are really about — a page
// that tracked either itself would pass a spec and lie to a player.

import { Then, When } from "@cucumber/cucumber";

import * as apiStub from "../support/api-stub.mjs";
import { world, PATIENCE } from "../support/hooks.mjs";
import { say } from "./play.steps.mjs";

function standing(who) {
  return world.page.getByTestId(`standing-${who}`);
}

When(
  "I say {string} and gary awards {string} {int}",
  async function (message, who, amount) {
    apiStub.garyWill({ award: { who, amount } });
    await say(message);
  },
);

Then("{string} should show as level {int}", async function (who, level) {
  await world.page.waitForFunction(
    ([name, wanted]) =>
      document
        .querySelector(`[data-testid="standing-${name}"]`)
        ?.textContent?.includes(`level ${wanted}`) ?? false,
    [who, level],
    { timeout: PATIENCE },
  );
});

Then(
  "{string} should show {int} of the {int} they need",
  async function (who, have, needed) {
    const text = await standing(who).innerText();
    if (!text.includes(`${have}/${needed} xp`)) {
      throw new Error(`${who} shows ${text}`);
    }
  },
);

Then("the transcript should show an award to {string}", async function (who) {
  const awards = await world.page.getByTestId("award").allInnerTexts();
  if (!awards.some((one) => one.includes(who))) {
    throw new Error(`no award naming ${who}: ${JSON.stringify(awards)}`);
  }
});

Then("the award should say what it was for", async function () {
  const awards = await world.page.getByTestId("award").allInnerTexts();
  if (!awards.some((one) => one.includes("for "))) {
    throw new Error(`no award said what it was for: ${JSON.stringify(awards)}`);
  }
});

Then(
  "the transcript should show {string} reaching level {int}",
  async function (who, level) {
    const levels = await world.page.getByTestId("level").allInnerTexts();
    if (!levels.some((one) => one.includes(who) && one.includes(`level ${level}`))) {
      throw new Error(`${who} did not reach ${level}: ${JSON.stringify(levels)}`);
    }
  },
);

Then("it should say what hit points that brought", async function () {
  const levels = await world.page.getByTestId("level").allInnerTexts();
  if (!levels.some((one) => /\d+ hit points/.test(one))) {
    throw new Error(`no hit points on a level: ${JSON.stringify(levels)}`);
  }
});
