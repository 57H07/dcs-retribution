import { ConfigFile } from "@rtk-query/codegen-openapi";

const config: ConfigFile = {
  // Written by `python -m game.server.openapischema` (no server needed).
  schemaFile: "./openapi.json",
  apiFile: "./src/api/baseApi.ts",
  apiImport: "baseApi",
  outputFile: "./src/api/_liberationApi.ts",
  exportName: "_liberationApi",
  hooks: true,
};

export default config;
