const config = {
  paths: ["features/**/*.feature"],
  import: ["features/steps/**/*.ts"],
  format: ["summary", "progress-bar"],
  formatOptions: { snippetInterface: "async-await" },
};

export default config;
