"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

const subscribeNoop = () => () => {};

/**
 * True only once running in the browser. useSyncExternalStore (rather
 * than the classic useEffect+setState "mounted" flag) avoids a
 * setState-in-effect render cascade for what's fundamentally a
 * synchronous "am I on the client" read.
 */
function useIsClient(): boolean {
  return useSyncExternalStore(
    subscribeNoop,
    () => true,
    () => false
  );
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isClient = useIsClient();

  // Avoids a hydration mismatch: the server has no idea what the
  // browser's/system's theme preference is, so render nothing themed
  // until after mount.
  if (!isClient) {
    return <Button variant="ghost" size="icon" aria-label="Toggle theme" disabled />;
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label="Toggle theme"
      onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
    >
      {resolvedTheme === "dark" ? <Sun /> : <Moon />}
    </Button>
  );
}