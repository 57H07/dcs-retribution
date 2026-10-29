/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API key for a client started on its own; see client/README.md. */
  readonly VITE_API_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
