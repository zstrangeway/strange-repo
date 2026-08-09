import assert from "node:assert/strict";
import { When, Then, World, setWorldConstructor } from "@cucumber/cucumber";
import { GET } from "../../src/app/health/route";

class HealthWorld extends World {
  response: Response | null = null;

  get result(): Response {
    assert.ok(this.response, "the health endpoint has not been called yet");
    return this.response;
  }
}

setWorldConstructor(HealthWorld);

When("the health endpoint is called", async function (this: HealthWorld) {
  this.response = await GET();
});

Then(
  "the health response status is {int}",
  function (this: HealthWorld, expected: number) {
    assert.equal(this.result.status, expected);
  },
);

Then(
  "the reported status is {string}",
  async function (this: HealthWorld, expected: string) {
    const body = (await this.result.json()) as { status: string };
    assert.equal(body.status, expected);
  },
);
