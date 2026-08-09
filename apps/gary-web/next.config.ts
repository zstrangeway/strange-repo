import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Bundle a self-contained server for the container image.
  output: "standalone",
  // Trace from the workspace root so pnpm-linked dependencies are included.
  outputFileTracingRoot: path.join(import.meta.dirname, "../.."),
};

export default nextConfig;
