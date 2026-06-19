// Public surface of @smart-accounting/api-types.
//
// Per plan §1.6 (M1):
//   - Re-exports `paths` and `components` from `./api.d.ts` (the openapi-typescript output).
//   - Adds zod schemas mirroring the most-validated request bodies — useful for the Mini-App
//     to parse user input before sending to the API and for runtime guards on responses.
//
// Generated via `pnpm types:gen` (turbo task) from a running apps/api at http://localhost:8000.
// Regenerate after every API contract change.
