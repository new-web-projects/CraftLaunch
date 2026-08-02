/**
 * Generates one idempotency key per booking-creation attempt, sent as
 * the `Idempotency-Key` header (see api-client.ts's `createBooking`).
 * Regenerate on each fresh visit to the create-booking form, but keep
 * the same key across retries of the same submission (e.g. a network
 * error) so a resubmit doesn't create a duplicate — the backend
 * rejects a second booking with a key it's already seen
 * (bookings/validators.py::check_duplicate_submission).
 */
export function generateIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for any environment without crypto.randomUUID (very old
  // browsers) — not cryptographically strong, but this key's only job
  // is to be unique-enough per form session, not to be unguessable.
  return `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}