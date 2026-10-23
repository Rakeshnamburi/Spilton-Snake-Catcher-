import {readFileSync} from "node:fs";

const web = readFileSync(new URL("../apps/web/lib/i18n.tsx", import.meta.url), "utf8");
const mobile = readFileSync(new URL("../apps/mobile/services/i18n.tsx", import.meta.url), "utf8");

const checks = [
  [web, ["nav.profile", "auth.signIn", "profile.save", "profile.requestExport", "profile.requestDeletion", "marketplace.search", "booking.mine"], key => `"${key}"`],
  [mobile, ["navNearby", "navBookings", "navTracking", "profileSave", "profileExport", "profileDelete", "marketplaceSearch", "bookingView"], key => `${key}:`],
];

const failures = [];
for (const [source, keys, tokenFor] of checks) {
  for (const key of keys) {
    const token = tokenFor(key);
    const occurrences = source.split(token).length - 1;
    if (occurrences < 5) failures.push(`${key}: expected 5 locale entries, found ${occurrences}`);
  }
}

for (const locale of ["en", "te", "ta", "kn", "ml"]) {
  if (!web.includes(locale === "en" ? "const en:" : `const ${locale}:`)) failures.push(`web locale missing: ${locale}`);
  if (!mobile.includes(locale === "en" ? "en: ENGLISH" : `${locale}: {`)) failures.push(`mobile locale missing: ${locale}`);
}

if (failures.length) {
  console.error(`Locale quality gate failed:\n- ${failures.join("\n- ")}`);
  process.exit(1);
}
console.log("Locale quality gate passed for English, Telugu, Tamil, Kannada, and Malayalam primary account/marketplace keys.");
