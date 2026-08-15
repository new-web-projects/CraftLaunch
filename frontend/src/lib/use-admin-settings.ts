"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/contexts/auth-context";

/**
 * Every admin settings page (Website, Brand, General, SEO, Storage,
 * Email, Payment, Feature Flags) needs the same three things: load
 * the current row on mount, PATCH on save, and show loading/error/
 * success feedback around that. Pulling that out here once instead
 * of repeating it eight times is what keeps each page's own file
 * down to just its fields and layout.
 */
export function useAdminSettings<T>(getter: () => Promise<T>, updater: (data: Partial<T>) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const load = useCallback(() => {
    getter()
      .then((result) => {
        setData(result);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, [getter]);

  useEffect(() => {
    load();
  }, [load]);

  function reload() {
    // Called from the Retry button's onClick (an event handler, not
    // an effect) — safe to setState synchronously here, unlike inside
    // the mount effect above, which relies on status already starting
    // as "loading" via useState's initial value instead.
    setStatus("loading");
    load();
  }

  async function save(patch: Partial<T>) {
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      const result = await updater(patch);
      setData(result);
      setSaved(true);
      return result;
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.body.detail ?? "Save failed." : "Save failed.");
      throw err;
    } finally {
      setSaving(false);
    }
  }

  return { data, status, saving, saveError, saved, save, reload, setSaved };
}
