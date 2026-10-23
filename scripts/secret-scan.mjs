import {readFileSync, statSync} from "node:fs";
import {spawnSync} from "node:child_process";

const listed = spawnSync("git", ["ls-files", "--cached", "--others", "--exclude-standard"], {encoding:"utf8"});
if (listed.status !== 0) {
  console.error("Unable to enumerate repository files for secret scan.");
  process.exit(1);
}

const rules = [
  ["private key", /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/],
  ["GitHub token", /\b(?:ghp|github_pat)_[A-Za-z0-9_]{30,}\b/],
  ["AWS access key", /\bAKIA[0-9A-Z]{16}\b/],
  ["Slack token", /\bxox[baprs]-[A-Za-z0-9-]{20,}\b/],
];
const findings = [];
for (const file of listed.stdout.split(/\r?\n/).filter(Boolean)) {
  const normalized = file.replaceAll("\\", "/");
  if (normalized.includes("node_modules/") || normalized.endsWith("package-lock.json")) continue;
  if (/\/(?:\.env|\.env\.[^/]+)$/.test(`/${normalized}`) && !normalized.endsWith(".env.example")) {
    findings.push(`${normalized}: environment file must not be committed`);
    continue;
  }
  try {
    if (statSync(file).size > 2_000_000) continue;
    const content = readFileSync(file, "utf8");
    for (const [label, pattern] of rules) if (pattern.test(content)) findings.push(`${normalized}: possible ${label}`);
  } catch {
    // Non-text or transient files are outside this lightweight repository gate.
  }
}
if (findings.length) {
  console.error(`Secret scan failed:\n- ${findings.join("\n- ")}`);
  process.exit(1);
}
console.log("Secret scan passed: no tracked/unignored high-confidence credentials detected.");
