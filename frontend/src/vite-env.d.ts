/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_NFA_API?: string;
  readonly VITE_NFA_WS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
