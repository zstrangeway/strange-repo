const common = {
  paths: ["features/**/*.feature"],
  import: ["features/**/*.mjs"],
  format: ["progress"],
};

module.exports = {
  // The stubbed suite. Fast, and the default, so `pnpm test` stays quick.
  default: { ...common, tags: "not @fullstack" },

  // The real thing: a real gary-api on a throwaway database. Needs a Postgres
  // and gary-api's Python toolchain, which is why it is a separate run.
  e2e: { ...common, tags: "@fullstack" },
};
