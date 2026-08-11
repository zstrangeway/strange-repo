import assert from "node:assert/strict";

import { Then, When } from "@cucumber/cucumber";

import * as apiStub from "../support/api-stub.mjs";
import * as stack from "../support/stack.mjs";
import { browserOutput, world } from "../support/hooks.mjs";

// Both apps write one JSON object per line. Anything else in the output —
// `next dev`'s banner, uvicorn's startup — is not a log line and is skipped
// rather than failed on.
function objects(raw) {
  const found = [];
  for (const line of raw.split("\n")) {
    if (!line.trim().startsWith("{")) {
      continue;
    }
    try {
      found.push(JSON.parse(line));
    } catch {
      // A partial line, mid-write. It will be whole on the next read.
    }
  }
  return found;
}

const webLines = () => objects(browserOutput());
const apiLines = () => objects(stack.apiOutput());

/**
 * Waits for a line to turn up rather than assuming it already has.
 *
 * The page has finished loading, but the server's write to the pipe and our
 * read of it are two different events. Without this the assertion races the
 * plumbing and fails perhaps one run in twenty.
 */
async function waitForLine(read, matches, what, timeoutMs = 10_000) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const found = read().filter(matches);
    if (found.length > 0) {
      return found.at(-1);
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  throw new Error(`no ${what} within ${timeoutMs}ms. The log held:\n${JSON.stringify(read(), null, 2)}`);
}

When(
  'I open the home page with {string} set to {string}',
  async function (header, value) {
    await world.page.setExtraHTTPHeaders({ [header]: value });
    await world.page.goto(`${world.baseUrl}/`, { waitUntil: "domcontentloaded" });
  },
);

Then("gary-web should have logged the call it made to gary-api", async function () {
  world.webCall = await waitForLine(
    webLines,
    (line) => line.message === "api.call" && line.app === "gary-web",
    "api.call line from gary-web",
  );

  assert.ok(world.webCall.request_id, "the line carries no request id");
});

Then("gary-api should have logged receiving that call", async function () {
  await waitForLine(
    apiLines,
    (line) =>
      line.message === "http.request" &&
      line.app === "gary-api" &&
      line.path === world.webCall.path,
    `http.request line from gary-api for ${world.webCall.path}`,
  );

  // Every one of them, not the last. A page can call the same endpoint more
  // than once — React runs mount effects twice in development, and the
  // campaigns page fetches on mount — and then "the last line" means
  // different requests in the two logs, because gary-web logs when a call
  // finishes and gary-api logs when it arrives. Pairing on that basis fails
  // about one run in ten and says nothing true when it does.
  world.apiCalls = apiLines().filter(
    (line) =>
      line.message === "http.request" &&
      line.app === "gary-api" &&
      line.path === world.webCall.path,
  );
});

Then("the two lines should carry the same request id", function () {
  // The property: gary-api kept the id it was handed rather than minting its
  // own, so one user action is findable in both logs. Matched by id across
  // whatever gary-api recorded for that path, which is true however many
  // times the page called it.
  const seen = world.apiCalls.map((line) => line.request_id);

  assert.ok(
    seen.includes(world.webCall.request_id),
    "the two apps logged the same call under different ids, so the two logs" +
      ` cannot be joined. gary-web sent ${world.webCall.request_id} for` +
      ` ${world.webCall.path}; gary-api recorded ${JSON.stringify(seen)}`,
  );
});

Then(
  'no line in either log should have {string} set to {string}',
  function (field, value) {
    const offending = [...webLines(), ...apiLines()].filter((line) => line[field] === value);
    assert.deepEqual(
      offending,
      [],
      `a value the browser chose reached the logs as ${field}`,
    );
  },
);

When("gary-api starts answering with something that is not JSON", function () {
  apiStub.answerWithGarbage();
});

Then(
  'gary-web should have logged a {string} line for {string}',
  async function (message, path) {
    world.serverError = await waitForLine(
      webLines,
      (line) => line.message === message && line.path === path,
      `${message} line for ${path}`,
    );
  },
);

Then("that line should name the error type and message", function () {
  const error = world.serverError.error;
  assert.ok(error, `no error object on the line: ${JSON.stringify(world.serverError)}`);
  assert.ok(error.type, "the error carries no type");
  assert.ok(error.message, "the error carries no message");
});
