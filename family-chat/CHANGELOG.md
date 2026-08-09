# Changelog

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
