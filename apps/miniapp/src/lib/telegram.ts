// Telegram WebApp helpers.
//
// Per plan §1.6 (M1):
//   - getInitData(): pulls the raw initData string from window.Telegram.WebApp.initData.
//   - getInitDataUnsafe(): typed access to user, chat, language_code without HMAC verification
//     (server-side verification still required — this is read-only convenience for the UI).
//   - onFocus(callback): re-runs the auth handshake when the WebApp regains focus (D12 refresh model).
//   - openInvoice / requestWriteAccess wrappers if we ever need them (out of scope at v1.0).
//
// These helpers wrap @telegram-apps/sdk-react so we have one place to swap if the SDK changes.
