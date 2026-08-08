# Changelog

## 2.1.1

### Fixed
- **Styling occasionally still didn't apply on reload**, even after the 2.1.0 cache-busting fix. The remaining cause looks like a timing race in Home Assistant's ingress "soft" panel reload: sub-resource requests (like the CSS file) can occasionally fire before the ingress session is fully established and fail silently, while a manual refresh happens later and succeeds. The stylesheet is now inlined directly into the page's HTML instead of loaded as a separate request, so it can no longer race against anything — if the page loaded, the styling is already in it.

## 2.1.0

### Fixed
- **Chat wasn't sending messages.** The Socket.IO client connected to the wrong path under Home Assistant's ingress proxy (it ignored the ingress URL prefix), so the connection silently failed. It now derives the correct path from the current page URL. The Socket.IO client library is also now bundled locally instead of loaded from a CDN, so it no longer depends on outbound internet access.
- **Renaming users gave a 404.** Admin panel redirects used plain root-relative paths, which don't account for the ingress prefix either. Redirects now read the `X-Ingress-Path` header Home Assistant provides and rebuild the correct URL (with a check to prevent that header being spoofed into an open redirect).
- **Message history didn't reload.** Every API call (`/api/messages`, `/api/emojis`, uploads) and every uploaded file/emoji URL used the same kind of root-relative path, so they 404'd under ingress the same way. All of these now resolve relative to the current ingress-aware URL. Messages were never actually being lost — they just weren't loading back in.
- **Styling didn't apply until a manual refresh.** Home Assistant's "soft" sidebar reload could reuse a stale cached copy of the CSS. Static assets are now cache-busted with a version query string and served with `Cache-Control: no-cache` so they always revalidate.
- Custom emoji upload no longer guesses its own file URL client-side (wrong timestamp/extension); the server now returns the real URL.

### Added
- **Admin panel** (`/admin`), password-protected, for renaming the two family members without restarting the add-on. Set the password via the new `admin_password` option in the add-on configuration.
- **Auto sign-in from Home Assistant.** The add-on now reads the Home Assistant ingress identity headers and can automatically sign someone in as a specific family member based on their HA login — configured per-account from the admin panel.
- **The manual "who's using the chat" picker has been removed.** Identity is now resolved entirely server-side from the logged-in Home Assistant account. If an HA account hasn't been mapped to a family member yet, the chat shows setup instructions instead of a picker. This also closes a gap where a client could previously claim to be any sender by editing the socket payload — the server no longer trusts client-supplied identity for messages, reactions, or emoji uploads.
- Add-on options actually apply now: previously `run.sh` hardcoded its own defaults and ignored `config.yaml`/the Configuration tab entirely. The server now reads Home Assistant's `/data/options.json` directly.

### Security
- Replaced the hardcoded Flask `SECRET_KEY` with a randomly generated one, persisted across restarts.
- Fixed a stored XSS: reaction emoji, uploaded file names/types, and custom emoji names were rendered into message HTML (including inline `onclick` attributes) without escaping. A crafted value in any of these could inject and run arbitrary JavaScript in every other connected family member's browser. All of these are now HTML-escaped, and file/emoji URLs are restricted to relative paths or `http(s)://` (blocking `javascript:`-scheme injection) before being used in `src`/`href` attributes.
