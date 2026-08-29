// The Node major has to be the same number in every place that names it.
//
// This exists because it was not. The image ran node 22 while `@types/node`
// said 20, and a dependabot bump then moved the types to 26 while the image
// stayed on 22 — which is the dangerous direction. Types ahead of the runtime
// compile happily against APIs that will not be there: `tsc` passes, the
// browser suite passes, and the failure arrives in production the first time
// somebody reaches for something Node 22 does not have.
//
// Nothing caught either mismatch because nothing was comparing them. There is
// no clever way to do this — it is four regexes and an equality — and the
// crude version run every build beats the careful version nobody wrote.

import { readFileSync } from "node:fs";
import path from "node:path";

const REPO = path.resolve(import.meta.dirname, "../../..");

const read = (relative) =>
  readFileSync(path.join(REPO, relative), "utf8");

function majors() {
  const found = [];

  const image = read("apps/gary-web/Dockerfile").match(/^FROM node:(\d+)/m);
  if (image) found.push({ where: "apps/gary-web/Dockerfile", major: image[1] });

  // Every job, not the first: they are set separately and can drift apart.
  const workflow = read(".github/workflows/ci.yml");
  for (const [, major] of workflow.matchAll(/node-version:\s*(\d+)/g)) {
    found.push({ where: ".github/workflows/ci.yml", major });
  }

  const manifest = JSON.parse(read("apps/gary-web/package.json"));
  const types = manifest.devDependencies?.["@types/node"];
  if (types) {
    found.push({
      where: "apps/gary-web package.json @types/node",
      major: types.replace(/[^\d.]/g, "").split(".")[0],
    });
  }

  // The first number in the range, not every digit in it: ">=22 <23" is one
  // major expressed as two bounds, and stripping non-digits made it "2223".
  const engines = manifest.engines?.node?.match(/(\d+)/);
  if (engines) {
    found.push({
      where: "apps/gary-web package.json engines.node",
      major: engines[1],
    });
  }

  return found;
}

const found = majors();

// A check that found nothing to compare has not passed, it has abstained —
// and this one reads files by path, which is exactly what a directory move
// breaks silently.
if (found.length < 4) {
  console.error(
    `node alignment: only found ${found.length} places naming a Node major, ` +
      `expected at least 4 — the scan has probably lost a file`,
  );
  process.exit(1);
}

const disagreeing = [...new Set(found.map((one) => one.major))];

if (disagreeing.length > 1) {
  console.error("node alignment: these do not agree on the Node major\n");
  for (const { where, major } of found) {
    console.error(`  ${major.padEnd(4)} ${where}`);
  }
  console.error(
    "\nTypes ahead of the runtime is the dangerous direction: it compiles " +
      "and then fails where nobody is watching.",
  );
  process.exit(1);
}

console.log(
  `node alignment: ${found.length} places all say node ${disagreeing[0]}`,
);
