# Changelog

## 2.5.3

### Fixed
- The custom emoji upload form (text field, file picker, Upload button) could overflow and get clipped on narrower screens — it had no wrap behavior, so all three controls were forced onto one row regardless of available width. It now wraps properly, with the Upload button taking its own row.

### Changed
- "Manage Custom Emojis" moved out of the sidebar and into the Settings menu (✏️), alongside display name — one place for personal preferences instead of two separate entry points.

## 2.5.2

### Fixed
- **"My messages disappeared" after changing a display name.** Nothing was actually deleted — saving a display name reloads the page so the new name applies everywhere at once, but the page had no memory of which channel you'd been viewing, so a reload always landed you back on the first channel. If your messages were in a different channel, they were still there, just out of view. On top of that, the very first message load on any page open was hardcoded to always fetch the `general` channel specifically, regardless of which channel was actually selected. Both are fixed: the channel you're viewing is now remembered across reloads, and the initial message load always requests the channel that's actually showing.

## 2.5.1

### Fixed
- **Errors were invisible.** `run.sh` ran Python without unbuffered output, so anything printed to the log (including error tracebacks) could sit in a buffer and never actually appear in the add-on's log viewer. Fixed by setting `PYTHONUNBUFFERED=1`.
- Socket.IO event handlers (message sending, reactions, joining a channel) don't go through Flask's normal error handling — an exception in one could fail completely silently, with nothing in the log and nothing shown to the user. All of them now log full tracebacks and tell the person in the chat that something went wrong instead of just doing nothing.
- Found and fixed a real bug this surfaced immediately: the `connect` handler's function signature didn't accept the `auth` argument the installed Socket.IO version actually passes to it, so it was silently throwing an exception on *every single connection* — harmless in practice (connections still worked), but pure log noise once errors became visible, so worth fixing outright.
- Any uncaught exception in a regular page/API request is now also guaranteed to be logged with a full traceback.

## 2.5.0

### Added
- **Display name (alias) support.** Anyone can now set how their name appears in the chat, separate from their real Home Assistant name — via the new ✏️ settings button next to your name in the sidebar. Changing your alias updates every message you've ever sent, not just future ones (messages are attributed by your stable Home Assistant account internally, and the displayed name is resolved live, so a rename applies everywhere retroactively).
- **Admins can set anyone's display name.** A new "Display Names" section in the admin panel (`/admin`) lists every known Home Assistant account and lets an admin change any of their aliases, or clear one back to that person's real HA name. Note: "admin" here means whoever has the admin panel password, same as the rest of `/admin` — Home Assistant doesn't expose per-user admin status through ingress, so there's no way for the add-on to check HA's own admin role directly.

## 2.4.1

### Fixed
- Logging out of the admin panel now returns you to the chat instead of back to the admin login screen.

## 2.4.0

### Changed
- **Identity is now fully automatic — no admin mapping step at all.** Anyone who opens the chat from the Home Assistant sidebar is signed in as themselves, using their own Home Assistant display name (or login username if no display name is set). The admin panel's "Family Members" roster and "Auto sign-in" mapping section are gone entirely — there's nothing to configure. Sign-in works the moment someone with a Home Assistant account opens the chat for the first time.
- The member sidebar now shows everyone who's actually opened the chat, most recent first, instead of a manually maintained list.
- **The add-on is no longer reachable via its port directly** — only through the Home Assistant sidebar/ingress. The direct port mapping (`8099/tcp`) has been removed from the add-on configuration entirely; ingress doesn't need a published port to work, so removing it means the app simply isn't reachable from your LAN at all outside of Home Assistant. (If you're upgrading, the add-on needs to fully restart/recreate for this to take effect — check that the old port is no longer reachable after updating.)

### Removed
- The `username1`/`username2` add-on configuration options, the Family Members roster, and the HA-user mapping feature (superseded by fully automatic identity above).

## 2.3.0

### Added
- **Support for more than two people.** The app used to hardcode exactly two named identities ("Family Member 1/2"). It's now an open-ended roster, managed from the admin panel — add or remove people, rename anyone, no fixed limit. Existing installs are migrated automatically: your current two names carry over as the first two roster entries the first time this version starts, nothing is lost.
- Every roster member can be individually mapped to their Home Assistant account from the same "Auto sign-in from Home Assistant" section as before — this now lists all current members, not just two.

### Changed
- The old "rename the two family members" admin form is replaced by the new Family Members section (add/rename/remove, same place in `/admin`).
- The member sidebar in the chat now lists everyone in the roster instead of a fixed pair, with avatar colors cycling through a small palette so each person still gets a distinct look.

## 2.2.0

### Added
- **Channel management in the admin panel.** The four channels (general, family-plans, memories, shared-files) used to be hardcoded in the page template. They're now stored in the database and editable from `/admin` — add a channel with a name and icon, or delete one. At least one channel always has to exist. Deleting a channel just hides it from the sidebar; its messages stay in the database and come back if you re-add a channel with the same name.

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
