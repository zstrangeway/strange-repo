import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit .next/standalone with only the files the server needs, so the
  // production image does not have to carry node_modules.
  output: "standalone",
  // Trace from the workspace root: pnpm keeps dependencies outside this app.
  outputFileTracingRoot: path.join(import.meta.dirname, "../../"),
};

export default nextConfig;
