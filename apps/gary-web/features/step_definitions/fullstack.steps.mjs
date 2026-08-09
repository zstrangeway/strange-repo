import { When } from "@cucumber/cucumber";

import * as stack from "../support/stack.mjs";
import { world } from "../support/hooks.mjs";

// Reads the link out of gary-api's own log rather than being told it, so the
// mail seam, the link gary-api builds, and WEB_BASE_URL are all exercised.
When("I open the reset link gary-api emailed", async function () {
  const token = stack.emailedResetToken();
  await world.page.goto(
    `${world.baseUrl}/reset?token=${encodeURIComponent(token)}`,
    { waitUntil: "domcontentloaded" },
  );
});
