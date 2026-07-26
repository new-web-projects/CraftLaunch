import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a minimal, self-contained server bundle (only the files
  // actually needed at runtime) — what deployment/docker/frontend.Dockerfile
  // is built around. Vercel ignores this and uses its own pipeline, so it's
  // safe to leave on even if you deploy there instead of self-hosted Docker.
  output: "standalone",
};

export default nextConfig;
