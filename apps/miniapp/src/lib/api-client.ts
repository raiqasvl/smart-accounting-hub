// Typed API client for the Mini-App.
//
// Per plan §1.6 (M1) and §1 globalEnv `NEXT_PUBLIC_API_BASE_URL`:
//   - Wraps fetch() with the typed request/response shapes generated from FastAPI's OpenAPI
//     by `pnpm types:gen` (turbo task) into packages/api-types/src/api.d.ts.
//   - Adds Authorization: Bearer ${jwt} on every authenticated call.
//   - On 401: clears stored JWT, re-runs initData → JWT exchange (D12: Mini-App re-posts
//     fresh initData on focus events; on 401 we treat the JWT as expired and re-auth).
//   - Centralises error handling — translates {error: {code, params}} into thrown ApiError
//     instances that the UI can localise via Fluent.
