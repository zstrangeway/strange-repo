import assert from "node:assert/strict";
import {
  Given,
  When,
  Then,
  World,
  setWorldConstructor,
} from "@cucumber/cucumber";
import { greet } from "../../src/lib/greeting";

class GreetingWorld extends World {
  name: string | null = null;
  greeting = "";
}

setWorldConstructor(GreetingWorld);

Given(
  "the visitor is named {string}",
  function (this: GreetingWorld, name: string) {
    this.name = name;
  },
);

Given("the visitor has no name", function (this: GreetingWorld) {
  this.name = null;
});

When("the greeting is built", function (this: GreetingWorld) {
  this.greeting = greet(this.name);
});

Then(
  "the greeting reads {string}",
  function (this: GreetingWorld, expected: string) {
    assert.equal(this.greeting, expected);
  },
);
