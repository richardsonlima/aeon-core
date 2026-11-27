# Control plane

A small static web UI for the Æon runtime. It has no build step: plain HTML, one ES module and one stylesheet.

| File | Purpose |
|---|---|
| `index.html` | Page shell, landmarks, dialogs, Content-Security-Policy |
| `app.js` | Router, API client and the five pages |
| `i18n.js` | English and Portuguese strings, language toggle |
| `app.css` | Styles (light theme, tokens of the public site) |

## How it connects

The runtime serves this folder at `/ui/` (`aeon runtime start`), and `aeon ui` opens `/ui/#token=<token>`.
On load the page:

1. reads the token from the URL fragment, keeps it in `sessionStorage` for this tab and removes it from the address bar;
2. calls the runtime on the same origin with `Authorization: Bearer <token>`;
3. opens `/v1/decisions/stream?token=<token>` with `EventSource` (the browser cannot set headers there, the runtime accepts the query token for that one path).

If the token is missing the page asks for it. A `401` clears the stored token and asks again.

## Pages

- **Overview**: agents, mode switch (shadow or enforce, with confirmation), kill-switch, deviation against budget, Safe State reset, counters, audit health.
- **Decisions**: live stream plus history, filters by agent, axiom and level, pause and resume, at most 500 rows in the page.
- **Campaigns**: start a campaign, poll it, read the result and compare two. Unfavourable results are always shown.
- **Audit**: hash chain verification (optional expected head), latest records, JSONL and CSV export.
- **Claims**: `/v1/claims` with the status ladder specified, implemented, measured.

## No third-party requests

Everything loads from the runtime's own origin. The page declares `Content-Security-Policy: default-src 'self'; connect-src 'self'`, uses no inline scripts or styles, no CDN, no web fonts (font stacks name `Inter`, `Plus Jakarta Sans` and `JetBrains Mono` and fall back to system fonts) and no analytics. Server data is written with `textContent`, never as markup.

## Accessibility

Landmarks, skip link, visible focus, keyboard-operable controls, `aria-live` regions for the stream counter and errors, `prefers-reduced-motion` respected, `lang` follows the selected language. Language defaults to `navigator.language` and is remembered in `localStorage`.

## Packaging

Editable installs serve this folder directly. Wheels include it as `aeon/controlplane`.
