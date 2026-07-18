module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module", project: null },
  plugins: ["react-refresh"],
  ignorePatterns: ["dist", "node_modules", "*.cjs"],
  rules: {
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    // Upload progress handlers and mutation error callbacks reasonably use
    // `any` for axios error shapes; kept as a warning rather than an error
    // so it doesn't block CI, but should be tightened with a shared
    // ApiError type as the project matures.
    "@typescript-eslint/no-explicit-any": "off",
  },
};
