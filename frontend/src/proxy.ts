import { NextResponse, type NextRequest } from "next/server";

const SESSION_HINT_COOKIE = "craftlaunch_session";
const PROTECTED_PATHS = ["/profile"];

/**
 * This is a UX shortcut, not a security boundary: it only checks
 * whether the non-httpOnly hint cookie is present, never the real
 * refresh token (which this can't read anyway, by design) or the
 * access token (which lives in browser memory, not a cookie, and
 * never reaches the server this way). Actual authorization is
 * enforced by the Django API on every request regardless of what
 * this does. Runs on Node.js (not Edge) as of Next.js 16's proxy
 * convention — irrelevant here since nothing edge-specific is used.
 */
export function proxy(request: NextRequest) {
  const isProtected = PROTECTED_PATHS.some((path) => request.nextUrl.pathname.startsWith(path));
  if (!isProtected) return NextResponse.next();

  const hasHint = request.cookies.has(SESSION_HINT_COOKIE);
  if (!hasHint) {
    const url = request.nextUrl.clone();
    url.pathname = "/unauthorized";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/profile/:path*"],
};