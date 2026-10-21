import type { NextConfig } from "next";

const pages = ["training", "teams", "facility", "about", "schedule", "contact"];

const nextConfig: NextConfig = {
  transpilePackages: ["@gary/ui"],
  // The static export already emits these .html files. Mirror their addresses
  // in development, where Next normally serves only extensionless routes.
  ...(process.env.NODE_ENV === "development"
    ? {
        async rewrites() {
          return pages.map((page) => ({
            source: `/${page}.html`,
            destination: `/${page}`,
          }));
        },
      }
    : { output: "export" }),
};

export default nextConfig;
