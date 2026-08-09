import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a minimal, self-contained server bundle (only the files
  // actually needed at runtime) — what deployment/docker/frontend.Dockerfile
  // is built around. Vercel ignores this and uses its own pipeline, so it's
  // safe to leave on even if you deploy there instead of self-hosted Docker.
  output: "standalone",

  // Required for the Codespaces API proxy below to actually work. Next.js
  // normally 308-redirects any request ending in "/" to the same path
  // WITHOUT the slash, before rewrites() is even consulted. Every Django
  // URL in this project ends in "/" (Django convention), and Django's own
  // APPEND_SLASH then redirects the slash back on. Together those two
  // "helpful" redirects fight each other forever: request "/api/health/"
  // -> Next strips it to "/api/health" -> proxied to Django ->
  // Django's APPEND_SLASH sends it back to "/api/health/" -> Next strips
  // it again -> ... This is what an infinite-redirect loop looks like from
  // the browser's perspective, and exactly why the frontend showed "API
  // unreachable" even though the backend was completely healthy on its own.
  // skipTrailingSlashRedirect turns off Next's half of that fight, so the
  // trailing slash survives untouched all the way to Django, which matches
  // it correctly on the first try. (Confirmed against Next.js 16.2.11 with
  // Turbopack by reproducing the exact loop and then re-testing with this
  // flag — see the write-up in the response this file was delivered with.)
  skipTrailingSlashRedirect: true,

  // Codespaces-only: when NEXT_PUBLIC_API_URL is left empty (see
  // .env.local / scripts/codespaces-setup.sh), proxy same-origin /api/*
  // calls through to the Django dev server running in this same
  // container. The browser then only ever talks to one origin (port
  // 3000), so cross-subdomain cookies and CORS never come into play
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