// Replaces the "react-app" preset that came with react-scripts. Like that
// preset it keeps to correctness rules (no style rules: Prettier owns
// formatting); the stricter typescript-eslint presets are left for later.
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["build", "coverage", "src/components/ruler/leaflet-ruler.d.ts"] },
  {
    files: ["src/**/*.{ts,tsx}"],
    extends: [tseslint.configs.base],
    languageOptions: {
      globals: { ...globals.browser },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "no-debugger": "error",
      "no-dupe-keys": "error",
      "no-duplicate-case": "error",
      "no-unreachable": "warn",
      "no-self-assign": "warn",
      eqeqeq: ["warn", "smart"],
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { args: "none", ignoreRestSiblings: true },
      ],
    },
  }
);
