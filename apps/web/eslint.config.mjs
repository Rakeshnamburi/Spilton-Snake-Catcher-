import {defineConfig, globalIgnores} from "eslint/config";
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextCoreWebVitals,
  ...nextTypeScript,
  {
    rules: {
      // Client-side API loading and persisted preferences intentionally initialize state in effects.
      "react-hooks/set-state-in-effect": "off",
      // React Hook Form's watch API is safe here, but cannot be analyzed by the optional compiler rule.
      "react-hooks/incompatible-library": "off",
    },
  },
  globalIgnores([".next/**", "node_modules/**", "next-env.d.ts"]),
]);
