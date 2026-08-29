// Every place that names a runtime version has to name the same one.
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

// Python, too. Moving gary-api to 3.13 turned up a `.python-version` that
// nothing else knew about — a fourth place naming the version, found only
// because uv refused to sync against it. That is precisely the shape this
// exists to catch, so it is not left to Node alone.
function pythonMajors() {
  const found = [];

  const image = read("apps/gary-api/Dockerfile").match(/^FROM python:(\d+\.\d+)/m);
  if (image) found.push({ where: "apps/gary-api/Dockerfile", major: image[1] });

  // Both Python apps, not just gary-api. scout is a fourth and fifth place
  // naming a version, and a place nothing compares is exactly what this file
  // exists to stop existing.
  for (const app of ["gary-api", "scout"]) {
    found.push({
      where: `apps/${app}/.python-version`,
      major: read(`apps/${app}/.python-version`).trim(),
    });

    const requires = read(`apps/${app}/pyproject.toml`).match(
      /requires-python\s*=\s*"[^\d]*(\d+\.\d+)"/,
    );
    if (requires) {
      found.push({ where: `apps/${app}/pyproject.toml`, major: requires[1] });
    }
  }

  return found;
}

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

// A check that found nothing to compare has not passed, it has abstained —
// and this one reads files by path, which is exactly what a directory move
// breaks silently.
function agree(runtime, found, least) {
  if (found.length < least) {
    console.error(
      `${runtime}: only found ${found.length} places naming a version, ` +
        `expected at least ${least} — the scan has probably lost a file`,
    );
    return false;
  }

  const distinct = [...new Set(found.map((one) => one.major))];
  if (distinct.length > 1) {
    console.error(`${runtime}: these do not agree\n`);
    for (const { where, major } of found) {
      console.error(`  ${major.padEnd(6)} ${where}`);
    }
    console.error(
      "\nAhead of the runtime is the dangerous direction: it builds and " +
        "then fails where nobody is watching.",
    );
    return false;
  }

  console.log(
    `${runtime}: ${found.length} places all say ${distinct[0]}`,
  );
  return true;
}

const ok = [
  agree("node", majors(), 4),
  agree("python", pythonMajors(), 5),
].every(Boolean);

process.exit(ok ? 0 : 1);
