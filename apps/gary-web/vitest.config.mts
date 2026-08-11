import path from "node:path";
import { defineConfig } from "vitest/config";

// The coverage gate is scoped to src/lib on purpose. Everything else in this
// app is an async Server Component or a Server Action, and Next's own testing
// guide says to cover those end to end rather than with unit tests — which the
// Gherkin suite does. A gate that swept them in would report a number it had
// not earned.
//
// Route handlers are the exception, and only for what end-to-end cannot reach:
// they answer a provider's redirect, and the specs run without a proxy in
// front, so nothing there can tell a URL built from the public host from one
// built from the address the server is bound to. Those tests run; they are
// still left out of what is measured, so the gate keeps meaning src/lib.
export default defineConfig({
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "src") },
  },
  test: {
    include: ["src/lib/**/*.test.ts", "src/app/**/*.test.ts"],
    environment: "node",
    coverage: {
      // The provider Next's own Jest example picks.
      provider: "v8",
      include: ["src/lib/**/*.ts"],
      exclude: ["src/lib/**/*.test.ts"],
      // skipFull passed to the text reporter directly: at the top level it
      // was ignored, and the table then hid every file sitting at 100% —
      // a passing run printed nothing, which reads like measuring nothing.
      reporter: [["text", { skipFull: false }], ["html", {}]],
      thresholds: { lines: 100, functions: 100, branches: 100, statements: 100 },
    },
  },
});
