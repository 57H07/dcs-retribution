# DCS Retribution Client

This is a React app for the front-end of DCS Retribution. It is a work in
progress that just barely implements the map. This is not useful for players
yet.

For development, set the following environment variables when launching DCS
Liberation (the Qt UI):

- `CORS_ALLOW_DEBUG_SERVER=true`

  This will allow the front-end to make requests to the server, as long as the
  front-end is running on http://localhost:3000.

Then, run `npm start` to start the development server. Launch the Qt UI with
`--new-map --dev` to connect the webview to the development server, or navigate
to http://localhost:3000 in your browser.

Commands and the event stream need the server's API key, which the Qt UI passes
in the page URL (`?apiKey=`). To use the dev server from a browser or Electron
instead, fix the key: add `SERVER_API_KEY=<any value>` to `serverconfig.env`
(next to the Qt UI) and `VITE_API_KEY=<the same value>` to `client/.env.local`.
See `docs/dev/api-commands.md`.

## Regenerating the API stubs

The backend uses FastAPI which exposes `/openapi.json`. This is consumed by
`@rtk-query/codegen-openapi` to automatically generate the API stubs in
`src/api/liberationApi.ts`.

If you make a change to the API surface the typescript API will need to be
regenerated. To do this, first launch Liberation (to start the backend) and run

```powershell
npm run regenerate-api
```

See https://redux-toolkit.js.org/rtk-query/usage/code-generation for more
information.

## Available Scripts

The client is built with [Vite](https://vite.dev/) and tested with
[Vitest](https://vitest.dev/) and Testing Library.

- `npm start`: development server on http://localhost:3000 with hot reload.
  The design system catalog (`src/ui/`, every component in its states) is at
  http://localhost:3000/catalog.html; it is not part of the build.
- `npm test`: runs the test suite once (`npm run test:watch` for watch mode,
  `npm test -- --coverage` for a coverage report).
- `npm run build`: type-checks, then builds the app to `build/` with relative
  asset paths, so the Qt UI can load `build/index.html` from disk; also writes
  the third-party licence notice to `build/NOTICE`.
- `npm run preview`: serves the production build on http://localhost:3000.
- `npm run lint` / `npm run typecheck`: ESLint and `tsc --noEmit`.
- `npm run electron`: opens the dev server in an Electron window.
