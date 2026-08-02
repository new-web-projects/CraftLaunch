import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a minimal, self-contained server bundle (only the files
  // actually needed at runtime) — what deployment/docker/frontend.Dockerfile
  // is built around. Vercel ignores this and uses its own pipeline, so it's
  // safe to leave on even if you deploy there instead of self-hosted Docker.
  output: "standalone",

  // Codespaces-only: when NEXT_PUBLIC_API_URL is left empty (set below),
  // proxy same-origin /api/* calls through to the Django dev server in
  // this same container. The browser then only ever talks to one origin
  // (port 3000), so cross-subdomain cookies and CORS never come into play
  // between Codespaces' separately-forwarded ports. Never active in
  // production, where NEXT_PUBLIC_API_URL is set to a real URL.
  async rewrites() {
    if (!process.env.NEXT_PUBLIC_API_URL) {
      return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }];
    }
    return [];
  },
};

export default nextConfig;