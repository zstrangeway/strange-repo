import { Given, When, Then } from "@cucumber/cucumber";

import { world } from "../support/hooks.mjs";

// Asserts on what was painted rather than on the class that caused it: the
// class is how the theme is implemented, the background is what someone sees.
// Measured through a canvas because computed colours serialise as lab() here,
// and the canvas is what turns any of those into channels we can weigh.
//
// The magenta first is a tripwire. If a future colour format is one canvas
// cannot parse, fillStyle keeps its previous value, and magenta sits between
// the two thresholds — so the step fails and reports what it measured, rather
// than reading as "dark" and passing for the wrong reason.
function measureLuminance() {
  const context = document.createElement("canvas").getContext("2d");
  context.fillStyle = "#ff00ff";
  context.fillStyle = getComputedStyle(document.body).backgroundColor;
  context.fillRect(0, 0, 1, 1);
  const [r, g, b] = context.getImageData(0, 0, 1, 1).data;
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}

const DARK_BELOW = 0.3;
const LIGHT_ABOVE = 0.7;

Given("my system is set to {word}", async function (scheme) {
  await world.page.emulateMedia({ colorScheme: scheme });
});

When("I choose the {string} theme", async function (label) {
  await world.page.getByTestId("user-menu").click();
  const choice = world.page.getByRole("menuitemradio", { name: label });
  await choice.click();
  // The menu closes itself on choosing. Waiting for that keeps the next step
  // from clicking through a dropdown still sitting on top of the page.
  await choice.waitFor({ state: "hidden" });
});

Then("the page is {word}", async function (expected) {
  // Polled rather than read once: a stored choice is applied after mount, so
  // a freshly opened page is briefly whatever the system asked for.
  const deadline = Date.now() + 15_000;
  let measured;

  do {
    measured = await world.page.evaluate(measureLuminance);
    if (expected === "dark" ? measured < DARK_BELOW : measured > LIGHT_ABOVE) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  } while (Date.now() < deadline);

  throw new Error(
    `expected a ${expected} page, measured luminance ${measured.toFixed(3)}`,
  );
});
