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

setDefaultTimeout(120_000);

const WEB_PORT = 3999;

export const world = {
  // localhost, not 127.0.0.1: `next dev` blocks cross-origin requests for
  // dev assets, and it treats a different hostname for the same address as
  // cross-origin — the page loads but its scripts 403 and it never hydrates.
  baseUrl: `http://localhost:${WEB_PORT}`,
  browser: null,
  page: null,
  resetToken: null,
};

let webServer = null;

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
  await apiStub.start();

  webServer = spawn(
    "node_modules/.bin/next",
    ["dev", "--port", String(WEB_PORT)],
    {
      env: { ...process.env, GARY_API_URL: apiStub.BASE_URL },
      stdio: "ignore",
    },
  );

  await waitForServer(world.baseUrl, 90_000);

  world.browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined,
  });
});

Before(async function () {
  // The stub holds accounts in memory, so it has to be emptied between
  // scenarios or one scenario's user signs the next one in.
  await apiStub.start();
  apiStub.reset();
  world.resetToken = null;
  world.page = await world.browser.newPage();
});

After(async function () {
  await world.page?.close();
  world.page = null;
});

AfterAll(async function () {
  await world.browser?.close();
  webServer?.kill();
  await apiStub.stop();
});
