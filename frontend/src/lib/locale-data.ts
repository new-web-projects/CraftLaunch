// ISO 3166-1 alpha-2 codes. Intl.DisplayNames can turn a code into a
// localized name, but there's no built-in "list all codes" API, so
// this list of codes is the one thing that has to be hand-maintained —
// everything else (the actual display names) comes from the browser.
const COUNTRY_CODES = [
  "US", "GB", "CA", "AU", "NZ", "IE", "IN", "PK", "BD", "LK", "NP",
  "DE", "FR", "ES", "IT", "PT", "NL", "BE", "CH", "AT", "SE", "NO",
  "DK", "FI", "PL", "CZ", "GR", "TR", "RU", "UA",
  "CN", "JP", "KR", "SG", "MY", "TH", "VN", "PH", "ID", "HK", "TW",
  "AE", "SA", "IL", "EG", "NG", "KE", "ZA", "GH",
  "BR", "MX", "AR", "CL", "CO", "PE",
] as const;

export function countryOptions(locale = "en"): { value: string; label: string }[] {
  const names = new Intl.DisplayNames([locale], { type: "region" });
  return COUNTRY_CODES.map((code) => ({ value: code, label: names.of(code) ?? code })).sort((a, b) =>
    a.label.localeCompare(b.label)
  );
}

export function timezoneOptions(): { value: string; label: string }[] {
  const zones =
    typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : ["UTC"];
  return zones.map((zone) => ({ value: zone, label: zone.replace(/_/g, " ") }));
}

const LANGUAGE_CODES = [
  "en", "es", "fr", "de", "pt", "it", "nl", "ru", "tr", "pl",
  "hi", "bn", "ur", "ta", "te", "zh", "ja", "ko", "vi", "th", "id", "ar",
] as const;

export function languageOptions(locale = "en"): { value: string; label: string }[] {
  const names = new Intl.DisplayNames([locale], { type: "language" });
  return LANGUAGE_CODES.map((code) => ({ value: code, label: names.of(code) ?? code })).sort((a, b) =>
    a.label.localeCompare(b.label)
  );
}