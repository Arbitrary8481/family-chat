# Changelog

## 2.21.11

### Security
- **Open redirect via the `X-Ingress-Path` header (CodeQL: `py/url-redirection`).** The existing validation (must start with `/`, must not contain `:`) blocked absolute URLs like `http://evil.com`, but not protocol-relative ones like `//evil.com` — that string starts with `/` and has no colon, so it passed straight through. Browsers treat a redirect `Location` starting with `//` as pointing at a different host entirely, using whichever scheme the current page loaded over — a working open-redirect vector despite technically satisfying the old check. Fixed with a proper validation: reject anything with a `//` prefix, a URL scheme, or a host component (via `urlparse`), and normalize backslashes first, since browsers treat them as equivalent to forward slashes even though Python's `urlparse` does not. Verified directly against the real endpoint with `//evil.com`, `/\\evil.com`, `http://evil.com`, and `https://evil.com` — all now fall back to the safe in-app path — while confirming legitimate ingress prefixes and direct (no-header) access still work exactly as before.

## 2.21.10

### Security
- **CodeQL flagged the Flask session secret being written to disk unencrypted.** The literal suggestion (encrypt it) doesn't really apply to a signing key — encrypting it would just mean persisting a second key to decrypt the first, moving the problem rather than solving it. The actual, practical mitigation is restricting who can read the file at the OS level, which was missing: the file is now written with `0600` permissions (owner read/write only, nobody else). Applied retroactively too — an existing install's secret file (created by an older version, without this restriction) gets it applied on next start, without regenerating the secret itself, which would have invalidated everyone's session.

## 2.21.9

### Security
- **Flask bumped to `>=3.1.3`**, addressing a cache-poisoning-adjacent issue where accessing `session` via certain patterns (the `in` operator, checking keys without values) could skip setting the `Vary: Cookie` header a caching proxy needs to avoid serving one person's cached page to someone else. Checked first: this app was never actually exploitable by it — every response already gets an explicit `Cache-Control: no-store` (from an earlier security pass), which independently blocks the caching this bug relies on, and the app only ever accesses `session` via `.get()`, never the vulnerable key-only pattern. Bumped anyway rather than leave a known-fixed CVE sitting in a pinned version doing nothing for anyone.
- **This surfaced a real, unrelated breaking incompatibility**: `flask-socketio==5.3.6` (pinned exactly, not a minimum) turned out to be fundamentally broken against Flask 3.1.3's internal session handling — a real-time connection would fail outright (`AttributeError: property 'session' of 'RequestContext' object has no setter`), not something a REST-only smoke test would ever catch. Bumped to `flask-socketio>=5.6.1` to fix it, and verified with an actual live Socket.IO client end to end (genuine WebSocket transport, room join, message round-trip, held-open stability, clean disconnect) against a completely fresh install — not just confirming the server process starts.

## 2.21.8

### Security
- **python-socketio bumped to `>=5.16.2`**, addressing two CVEs: the pickle-deserialization RCE fixed in 5.14.0 (this app runs single-server with no message queue, so it was never actually exploitable here, but the fix is free) and a more recent memory-exhaustion DoS (5.16.2) where a client could submit a binary message, deliberately withhold its attachments, and leave the partial message held in server memory indefinitely — the fix requires binary packets to come from an authenticated client and cleans up any partial message left behind when a client disconnects. Verified with a live Socket.IO connection (real WebSocket transport, room join, message round-trip, clean disconnect) against a completely fresh install of the updated dependency set.

## 2.21.7

### Fixed
- **Opening the channel drawer on mobile garbled the header text** — the previous fix (raising the header above the drawer so its toggle button stayed clickable) caused the header to visually overlap the drawer's own "🏠 [server name]" heading, since both occupied the same strip at the top of the screen. Reverted that approach in favor of a proper fix: a dedicated ✕ close button now lives inside the drawer itself, next to the settings pencil in the user panel at the bottom. The header goes back to sitting normally behind the drawer (no more text collision), and closing the drawer no longer depends on being able to see or tap anything in the header while it's open — the close button, tapping the dimmed backdrop, or picking a channel all still work.

## 2.21.6

### Fixed
- **The channel-list toggle button appeared to vanish on mobile — it was actually being covered up.** The header had no explicit stacking order, so when the channel drawer was open (a full-height overlay from the left edge, covering the header's left portion), it rendered on top of the very button you'd tap to close it, making it look like the button had disappeared entirely rather than just being open. The header now always stays above the drawer, so the toggle button (and the rest of the header) is reachable no matter what state the drawer is in.

## 2.21.5

### Fixed
- **The channel-list toggle button used the ☰ hamburger icon — the same icon Home Assistant's own frontend uses for its own navigation drawer.** On mobile, where HA shows its own app bar around the add-on's content, this made it easy to tap HA's own menu instead of the chat's button, or just be confused about which one you were looking at. Replaced with a distinct sidebar-toggle icon (a panel with a divider line) that doesn't look like a generic app menu.

## 2.21.4

### Removed
- **The Discord-style "server picker" rail** (the narrow strip with the Home icon on the far left) — this app only ever has the one workspace, so it never did anything besides take up space. Removed entirely, along with several related CSS rules that turned out to be fully dead code already (`.server-divider`, `.add-server` — styled for elements that were never actually in the page). The channel sidebar now sits flush against the left edge on both desktop and mobile; the mobile drawer's toggle button lives solely in the header now.

## 2.21.3

### Changed
- **The server-list rail (Home icon + channel toggle) now collapses to zero width on mobile along with the channel drawer**, instead of permanently reserving 60px whether the drawer was open or not. Collapsed = the chat gets the full screen width, no dead space; opening the drawer (from the header's ☰, which stays reachable either way) brings the rail back alongside it, same as before.

## 2.21.2

### Added
- **A second, persistent way to open/close the channel drawer on mobile** — a ☰ button on the server-list rail (the narrow always-visible bar on the far left), alongside the existing one in the header. It stays put regardless of scroll position and can't get covered by anything, making it a more reliable target than the header button alone. Both buttons now stay in sync and reflect whether the drawer is currently open. Desktop is unaffected — this button only appears on phone-width screens.

## 2.21.1

### Fixed
- **Reverted the eventlet → threading migration from 2.20.0 — it broke real-time messaging.** Flask-SocketIO's `threading` async mode runs on Werkzeug's plain development server, which has no native WebSocket support at all. Every client silently fell back to HTTP long-polling: visible in the add-on log as the same session making a new `/socket.io/` request every ~150ms, eventually followed by `'Session is disconnected'`. Confirmed directly by Flask-SocketIO's own maintainer in their issue tracker: threading mode works "without WebSocket for now." Back on eventlet (still the CVE-2025-58068-patched `>=0.40.3` from 2.19.0, with `monkey_patch()` correctly called first) — verified with a live connection that stays on genuine WebSocket transport with zero polling traffic while connected, not just "the server boots." The deprecation warning in the log is back too; that trade was the right one to reverse. A non-eventlet path may be worth revisiting later (Flask-SocketIO mentions threading mode plus the `simple-websocket` package as a possible fix, though with mixed reliability reports) — but not as a same-day swap without dedicated testing.

## 2.21.0

### Fixed
- **The channel sidebar was completely inaccessible on any phone-width screen.** The mobile CSS was toggling a class (`.channel-sidebar.open`) that no JavaScript anywhere ever actually set — a leftover from before the desktop collapse/expand feature existed. On mobile the sidebar was permanently stuck off-screen with no way to open it at all. It's now a proper slide-over drawer using the same ☰ button and collapse system already used on desktop, with a dimmed backdrop you can tap to close it. First-time mobile visitors land on the chat with the drawer closed by default (desktop is unaffected — still opens by default there, as before); anyone who's explicitly toggled it either way has that choice remembered regardless of screen size.
- **The 😊 react / 🗑️ delete buttons on messages only ever appeared on hover** — completely unreachable on any touchscreen, since tapping a message doesn't produce a hover state the way a mouse does. Now shown permanently on touch devices and narrow screens.
- Picking a channel from the mobile drawer now closes it afterward, instead of leaving it covering the channel you just switched to.
- The 👥 member-list toggle button is now hidden on screens where the member list itself is already auto-hidden (below 1200px) — it used to stay visible and tappable while doing nothing.
- The static "Family communication center" subtitle next to the channel name is hidden on phone-width screens to make room for the buttons that actually do something.

## 2.20.0

### Changed
- **Migrated off eventlet entirely**, in favor of Flask-SocketIO's `threading` async mode. Eventlet is maintenance-only upstream (security/bugfixes only, no new features, and its own docs recommend new/ongoing projects avoid it) — this app now uses real OS threads instead of eventlet's green threads to get the same practical property (a slow request doesn't stall every other connected client), with no monkey-patching and no eventlet dependency at all. Verified with a live server boot, a genuine concurrency test (a 2-second slow request run alongside a fast one, confirming the fast one isn't blocked), and a real Socket.IO client connecting, joining a room, and successfully upgrading to a live WebSocket transport — all in a clean environment with eventlet not even installed.
- One tradeoff that comes with this: threading mode runs on Werkzeug's own server rather than a dedicated production WSGI server, which normally isn't recommended for handling untrusted traffic directly. That's an acceptable trade here specifically because this add-on is never reached directly — Home Assistant's ingress proxy is the only thing that ever talks to it (no direct port mapping — see config.yaml), and that proxy is the actual internet/LAN-facing component. Documented clearly in code in case that assumption ever needs to be revisited.

## 2.19.0

### Security
A full security review of the whole add-on. Fixed, in order of severity:

- **CVE-2025-58068**: `eventlet` (the actual WSGI server this app runs on) was pinned to 0.35.2, vulnerable to HTTP request smuggling. This app's entire identity model depends on Home Assistant's ingress proxy correctly sanitizing the `X-Remote-User-*` headers before forwarding requests — request smuggling is exactly the class of bug that can defeat that kind of front-end sanitization. Bumped to `>=0.40.3` and verified with a live server boot plus a full regression pass.
- **Unvalidated input reaching a privileged server-side API call**: the device name for push notifications went straight from client-supplied JSON into the URL path of a request made with this add-on's own Home Assistant API token — a crafted value could have targeted a completely different part of Home Assistant's API than intended. Fixed with strict allowlist validation, both where the value is saved and immediately before it's ever used to build a request.
- **`max_file_size` wasn't actually enforced.** It was computed from the add-on's configuration but never used — every upload was capped by a hardcoded 100MB regardless of what was configured. Now genuinely enforced via Flask's request-size limit, with a clean error message instead of a raw server error page when exceeded.
- **File upload routes had no identity check**, unlike every other state-changing route in the app. Not currently reachable by anyone outside Home Assistant (this add-on exposes no direct port), but inconsistent with the rest of the app's defense-in-depth and now fixed to match.
- **No brute-force protection on the admin login form.** Password comparison was already constant-time, but attempts were completely unlimited. Now locks out after 10 failed attempts for 5 minutes.
- **Custom emoji upload built its filename from unsanitized user input**, unlike the main upload route's correct use of `secure_filename()`. Confirmed this wasn't currently exploitable (the OS requires each intermediate directory in a traversal attempt to actually exist, which it never would here) — fixed anyway rather than relying on that.
- **Message length had no server-side limit.** A malicious or misbehaving client could post an arbitrarily large message, stored and re-sent to everyone on every future page load. Capped at 4000 characters.
- Session cookie hardening made explicit (`HttpOnly`, `SameSite=Lax`) rather than relying on Flask's version-dependent defaults.
- A single-character avatar initial was inserted into the page without escaping — confirmed not practically exploitable (it's mathematically impossible to form a complete HTML tag from one character), but fixed for consistency with the rest of the codebase's escaping discipline.

## 2.18.1

### Fixed
- **The real remaining cause of "images/messages load inconsistently on refresh, but a hard refresh always works."** The main page itself (`index.html`, served from `/`) had *no* cache-control header at all — the previous fix only covered `/static/` and `/api/`. A stale cached copy of the page references a stale cache-busted script.js URL, which can itself be served from an old cached copy — so a normal refresh could load an inconsistent mix of old and new files depending on exactly what the browser (or Home Assistant's ingress iframe) happened to have cached at that moment, while a hard refresh always bypasses all of that and gets the current version, which matches exactly what was reported. Every response from this add-on — the page, the scripts, the API, uploaded files — is now explicitly `no-store`, not just `no-cache`: given this is now the second stale-caching report through the ingress iframe specifically, `no-cache`'s revalidation doesn't seem to be reliably honored there, so this goes with the strictly stronger directive rather than continuing to rely on that.

## 2.18.0

### Fixed
- **Images loading inconsistently on refresh (root cause).** The server was started with `async_mode='eventlet'` but never actually called `eventlet.monkey_patch()` — meaning it never had the cooperative concurrency that setting is supposed to provide. In practice, any blocking call anywhere (a GIPHY search, a Home Assistant notification, even just serving a file from `/uploads/`) stalled the *entire* single-threaded process, not just that one request — including everyone else's in-flight image loads. A full page refresh fires off many concurrent image requests at once; if the process happened to be mid-stall from something else at that exact moment, a whole batch of them could time out together. This is now fixed at the source.
- **A missing `Content-Type` from the browser on some uploads silently downgraded a real image into a plain file-name attachment**, with no preview. Some browser/OS/file-type combinations just don't supply one. The image-vs-file decision now falls back to the file extension when there's no MIME type to go on, instead of assuming "not an image."
- **API responses (`/api/messages` etc.) had no cache-control headers at all**, leaving them cacheable by the browser or any proxy in the request path (Home Assistant's ingress always is one) — same category of bug already fixed for static assets a while back, just not applied to the API. Now explicitly `no-store`.
- **A failed fetch of message history used to fail completely silently**, looking exactly like an empty channel. Now shows a visible error instead.

## 2.17.0

### Changed
- **The admin panel is now tabbed** (Chat Name, Channels, Server Owner, Display Names), matching the vertical-tab layout the user Settings panel already uses, instead of one long scrolling page. Saving something in a tab now redirects back to that same tab rather than jumping to the top of the page.

## 2.16.0

### Added
- **Admin-configurable chat name.** The "🏠 Family Home" header at the top of the channel sidebar was hardcoded — it's now editable from the admin panel (new "Chat Name" section at the top), with a separate icon field. Leaving it blank falls back to the original default rather than saving empty.

## 2.15.0

### Added
- **Jump-to-bottom button.** Scroll up to read earlier messages and a small ↓ button appears above the message box to take you back to the latest ones — with a badge showing how many new messages arrived while you were away, once there are any.
- Incoming messages no longer force-scroll you to the bottom if you'd scrolled up to read history — they still arrive right away, but the view no longer gets yanked out from under you. You only auto-follow new messages if you were already at the bottom when they came in.

## 2.14.0

### Added
- **Links in messages are now clickable.** Any `http://` or `https://` URL in a message (in the main chat and in search results) turns into a real link that opens in a new tab. Trailing punctuation like a sentence-ending period or a wrapping parenthesis is correctly excluded from the link itself. Message content is still fully escaped either way — this doesn't loosen anything about what's safe to post.

## 2.13.1

### Fixed
- **Pasting a screenshot only worked once per message.** The paste listener was only attached to the plain message box, but the first pasted image opens the caption/preview modal — which moves keyboard focus into the caption field. A second paste while focus was there never reached the handler at all. It's now a single document-level listener, so pasting works no matter what's currently focused.

## 2.13.0

### Added
- **Paste screenshots directly into the message box.** Copy a screenshot (or any image) and paste with Ctrl+V / Cmd+V while the message box is focused — it uploads and opens the same preview-and-caption flow as picking a file with 📎, no need to save it to disk first.

## 2.12.0

### Added
- **Server Owner.** An admin can designate one Home Assistant account as the "owner" from the admin panel (Settings section: Server Owner). The owner gets the same delete-any-message and delete-any-channel powers an admin has, but tied to their own Home Assistant login — no admin password needed, no visiting the admin panel. Channel deletion is now available right from the chat's own Settings (✏️ → Channels tab) for the owner and for anyone with an active admin session, alongside the add-channel form that already lived there. Leaving the owner unset (the default) changes nothing — those powers stay admin-only, exactly as before.

## 2.11.0

### Added
- **Delete your own messages.** A 🗑️ button appears alongside the reaction button (hover over a message) on anything you sent — deleting removes it instantly for everyone in that channel, including any reactions on it and, for uploaded files/images, the underlying file on disk. GIFs are never touched on disk since they're just a link to GIPHY, not a local file.
- **Admins can delete anyone's message.** Requires having signed into the admin panel (with the admin password) in that same browser first — the delete button then appears on every message, not just your own.

## 2.10.0

### Changed
- **Settings is now a vertical-tab panel** (Profile, Notifications, Channels, Emojis) instead of one long scrolling column — each category gets its own space, no more scrolling past notification settings to reach custom emojis.
- **Adding a channel moved from the admin panel into everyone's own Settings** (✏️ → Channels tab). Any family member can now add a channel without needing the admin password. Deleting a channel stays admin-only, since that's the more disruptive action.
- The old separate "Manage Custom Emojis" popup is gone — it's just the Emojis tab now.

## 2.9.3

### Fixed
- **A message being sent and nobody getting notified looked identical in the log to notifications working correctly and just not firing** — both were silent. Now logs an explicit line either way: "No notification subscribers for #channel" if nobody's subscribed, or "Notified X via Y" for each person actually notified, so a missing notification can be diagnosed straight from the add-on log instead of guessing.

## 2.9.2

### Added
- **Per-channel notification subscriptions.** Settings now shows a checkbox for each channel instead of one global on/off switch — you can be notified for #general and #plans but not #memories, for example. Anyone who already had the old all-channels toggle on gets automatically subscribed to every existing channel during the upgrade, so nobody's notifications silently turn off — narrow it down from there.

## 2.9.1

### Fixed
- **Selecting a device and saving in Settings closed the whole panel, making it look like the device picker had disappeared.** Saving your notification preference no longer closes Settings — it now shows a small "Saved" confirmation next to the buttons instead, so the dropdown stays right there to pick a different device and save again.

## 2.9.0

### Added
- **Push notifications for new messages, via Home Assistant.** Each person can opt in from Settings (✏️), choosing which of their devices to notify — the list is pulled live from Home Assistant's own `notify.*` services (created automatically by the HA Companion App on each phone), so there's nothing to type by hand. A "Send Test" button lets you confirm you picked the right device before relying on it.
  - You're never notified about your own messages.
  - Notifications are scoped to the channel a message was posted in.
  - No separate push service or API key is needed — this add-on now requests `homeassistant_api` access and calls Home Assistant's own REST API through the supervisor to trigger the notification. **Existing installs need to rebuild the add-on (not just restart it) for this new permission to take effect** — Settings → Add-ons → Family Chat → Rebuild.
  - Requires the Home Assistant Companion App to be installed and connected on each phone you want to notify; until then that person's device simply won't appear in the list.

## 2.8.4

### Fixed
- **Messages and reactions were broadcast to every connected browser regardless of which channel they were posted in**, not just people actually viewing that channel — invisible with one person on one device, since you only ever post into the channel you're looking at, but with multiple family members online at once, someone in #general could have messages meant for #memories or #plans appear directly in their view. Both are now scoped server-side to the channel they belong to.
- **Switching channels joined the new channel's live-update group without ever leaving the old one.** A single browser session that visited several channels over time would end up subscribed to all of them, which would have undermined the fix above the longer a tab stayed open. Switching channels now properly leaves the previous one first.

## 2.8.3

### Fixed
- **Reacting to a message with a custom emoji showed a bare count with no emoji (e.g. just "1").** Reactions were packed into a single string as `emoji:user` and unpacked by splitting on `:` — but a custom emoji reaction is stored as `:name:`, which already contains colons, so the split landed in the wrong place and corrupted both the emoji and the username. Reactions are now assembled from a separate query instead of a delimited string, so this can't happen regardless of what characters end up in an emoji name or username.
- **Reactions didn't appear until you reloaded the page.** The client's handler for incoming reaction updates was an empty stub, so reacting (or having someone else react) never updated what was on screen in real time.
- **Clicking a reaction you'd already placed didn't remove it.** It just added a duplicate row, inflating the count — even though the pill was already visually styled as "active" to suggest it was a toggle. Reacting a second time now actually un-reacts.

## 2.8.2

### Added
- **The emoji picker's search box now actually works.** Typing filters live across every category at once (so "cat" finds 🐱 even while the Food tab is showing) and matches your custom emojis by name too. Previously the search field was just a dead input. Emoji are matched against ~830 generated keyword names (e.g. 😍 → "smiling face with heart-eyes"), so search understands plain-English terms rather than the raw characters.

## 2.8.1

### Fixed
- **The 😊 "add reaction" button on messages popped up a plain browser prompt ("Enter emoji:") instead of a real picker.** It now opens the same full emoji picker used by the composer — tabs, search box, and custom emojis — positioned right next to the button you clicked. Picking an emoji reacts with it immediately; clicking the button again (or elsewhere) closes it.

## 2.8.0

### Added
- **Collapsible sidebars.** New ☰ and 👥 buttons in the chat header collapse/expand the channel list and member list independently. Each sidebar remembers its collapsed state across reloads.

## 2.7.0

### Added
- **GIF picker.** Click the new GIF button next to the emoji picker to search GIPHY (or browse what's trending) and post a GIF straight to the chat, no file upload needed. Requires a GIPHY API key set in the add-on configuration — the button is hidden until one is configured. The key is only ever used server-side; the browser talks to `/api/giphy/search` and `/api/giphy/trending` on this add-on, which proxies the request to GIPHY.

## 2.6.1

### Fixed
- **Reloading a channel with images/files didn't always land on the most recent message.** The scroll-to-bottom happened right after messages were inserted into the page, but attached images finish loading (and growing the page) afterward — landing you above the true bottom on channels with a lot of attachments. Loading a channel's history now re-corrects the scroll position as each image finishes loading, so it settles on the actual most recent message.

## 2.6.0

### Fixed
- **The 🔍 search and 📎 files buttons in the header never did anything.** They were calling functions that were never actually implemented in the original template — clicking them just silently failed. Both are now fully built.

### Added
- **Search.** Click 🔍 to search message text across *all* channels (not just the one you're viewing), most recent matches first. Click a result to jump to that channel; if the message is recent enough to already be loaded, it scrolls to and briefly highlights it. (Very old messages beyond a channel's most recent 100 will switch you to the right channel but won't auto-scroll yet — there's no "load older history" feature to support that until a future update.)
- **Shared files.** Click 📎 to see every file shared in the *current* channel — name, who sent it, size, and when — each one a direct link to open it.

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
