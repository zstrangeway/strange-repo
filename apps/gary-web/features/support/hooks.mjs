import { spawn } from "node:child_process";

import {
  AfterAll,
  BeforeAll,
  Before,
  After,
  setDefaultTimeout,
} from "@cucumber/cucumber";
import { chromium } from "playwright";

import * as apiStub from "./api-stub.mjs";
import * as stack from "./stack.mjs";

setDefaultTimeout(120_000);

const WEB_PORT = 3999;

// Set by the e2e profile. When on, gary-web talks to a real gary-api against a
// throwaway database; when off, to the in-memory stub.
export const fullStack = process.env.GARY_E2E === "1";

export const world = {
  // localhost, not 127.0.0.1: `next dev` blocks cross-origin requests for
  // dev assets, and it treats a different hostname for the same address as
  // cross-origin — the page loads but its scripts 403 and it never hydrates.
  baseUrl: `http://localhost:${WEB_PORT}`,
  browser: null,
  page: null,
  resetToken: null,
  verificationToken: null,
};

let webServer = null;
let webLog = "";

/** Everything gary-web's server has written since the last scenario began. */
export function webOutput() {
  return webLog;
}

async function waitForServer(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      await fetch(url);
      return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 250));
    }
  }

  throw new Error(`${url} did not come up within ${timeoutMs}ms`);
}

BeforeAll(async function () {
  let apiUrl;
  if (fullStack) {
    await stack.start();
    apiUrl = stack.API_URL;
  } else {
    await apiStub.start();
    apiUrl = apiStub.BASE_URL;
  }

  webServer = spawn(
    "node_modules/.bin/next",
    ["dev", "--port", String(WEB_PORT)],
    {
      env: { ...process.env, GARY_API_URL: apiUrl },
      // Piped rather than ignored: gary-web logs its calls to gary-api here,
      // and nowhere else. None of it reaches the browser, so a scenario that
      // wants to see it has to read the server's own output.
      stdio: ["ignore", "pipe", "pipe"],
    },
  );

  const collect = (chunk) => {
    webLog += chunk.toString();
  };
  webServer.stdout.on("data", collect);
  webServer.stderr.on("data", collect);

  await waitForServer(world.baseUrl, 90_000);

  world.browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined,
  });
});

// Selecting the profile is not the same as selecting the mode. Without this,
// `cucumber-js --profile e2e` runs the full-stack scenarios against the stub
// and most of them pass, which is a worse outcome than an error.
Before({ tags: "@fullstack" }, function () {
  if (!fullStack) {
    throw new Error(
      "@fullstack scenarios need GARY_E2E=1. Run `pnpm test:e2e`, which sets it.",
    );
  }
});

Before(async function () {
  // Either backing store has to be emptied between scenarios, or one
  // scenario's account signs the next one in.
  if (fullStack) {
    stack.reset();
  } else {
    await apiStub.start();
    apiStub.reset();
  }

  webLog = "";
  world.resetToken = null;
  world.verificationToken = null;
  world.page = await world.browser.newPage();
});

After(async function () {
  await world.page?.close();
  world.page = null;
});

AfterAll(async function () {
  await world.browser?.close();
  webServer?.kill();

  if (fullStack) {
    await stack.stop();
  } else {
    await apiStub.stop();
  }
});
