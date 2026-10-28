# Security Policy

## Reporting a vulnerability

Please send an email to highlysuspicioussender@gmail.com (yes, that is my email I use for this kind of stuff) if you find a security issue with the family chat and I will review it.

## Supported versions

Fixes are only made to the latest version. Keep the app updated from the Home Assistant app store to get them.

## How Family Chat is protected

- **Reachable only through Home Assistant.** The app has no port of its own. Every request comes through Home Assistant's ingress proxy, which only lets in people who are logged into Home Assistant. Connections from anywhere else, including other apps on Home Assistant's internal network, are refused.
- **Identity comes from Home Assistant, not the browser.** Who sent a message, reaction, vote or upload is taken from the login Home Assistant passes along, never from anything the browser sends.
- **Admin access is password-protected.** Admin login stays off until a password other than the default is set. The admin panel locks for 5 minutes after 10 wrong passwords, and admin sessions end whenever the app restarts, including after a password change. The server owner gets the same moderation powers through their Home Assistant login instead.
- **The container is locked down** by a custom AppArmor profile that only allows the files and network access the app needs.
- **Everything shown on the page is escaped**, including formatted messages, polls, file names and link previews.
- **Everything sent to the server is checked**, including messages, polls, votes, uploads and voice messages sent directly to it, bypassing the app.
- **Link previews only fetch public websites.** Requests to Home Assistant itself, your local network or cloud metadata addresses are refused, including through redirects or DNS tricks.
- **Responses are never cached** (`Cache-Control: no-store`), and every response sends `X-Content-Type-Options: nosniff`.
- **GitHub CodeQL** scans every pull request.

## Fixed security issues

Newest first. Each entry was fixed in the version shown.

### 2.56.0
A full security review of the app.
- **Other apps on Home Assistant's internal network could pose as any family member.** The app trusted the login details Home Assistant's ingress proxy adds to each request, but it accepted connections from any address. Any other app container on the same internal network could connect directly and send its own login details, including the server owner's. Only Home Assistant's ingress proxy (`172.30.32.2`) can connect now, as Home Assistant's developer docs require.
- **Deleting a message could delete someone else's file.** A message sent directly to the server can point at any file already stored, such as another person's photo, avatar or custom emoji. Deleting that message deleted the file with it. A file is now kept while anything else still uses it.
- **The default admin password worked.** `changeme` is printed in the app's own configuration and README, so any family member could log in as admin, download every message as a backup, or replace the database. Admin login now stays off until a real password is set. An empty password is treated the same way.
- **Admin sessions survived a password change.** Admin sessions now end whenever the app restarts, which a password change requires.
- **GIF messages could load an image from any website.** A message sent directly to the server could use any address as a GIF, and that website would see the address of everyone who opened the channel. GIFs must now come from GIPHY.
- **Reactions had no length limit.** A reaction sent directly to the server could store a huge string on any message. Reactions are now limited to 64 characters.
- **Uploads could overwrite each other.** Two files with the same name uploaded in the same second got the same stored name, so one replaced the other. Each upload now gets a name nothing else uses.

Reviewed and left as they are:
- Every route, socket event, template and page script was checked. Everything shown on the page is still escaped, uploads are still limited to safe file types, and SQL queries are all parameterized.
- No known vulnerabilities in the Python packages the app uses (checked with `pip-audit`).
- The app's container is built on Alpine 3.19, which no longer gets security updates. Moving to a newer base image needs testing on a real install, so it will be a separate update.
- Any family member can send push notifications through any `notify.*` service Home Assistant has, including someone else's phone. This is by design, since the device list comes from Home Assistant. Restricting it would need a way to link phones to people.

### 2.53.0
- **Channel reordering accepted a list that named the same channel twice.** Only the server owner or an admin can reorder, so this was low risk. Such a list is now rejected.

### 2.52.2
- **A specially crafted message could make the chat or the server very slow (ReDoS).** Some formatting patterns, and the code that trims punctuation off links, took time that grew with the square of a message's length. A 20,000-character message could stall the server for over a second each time it was summarized for a notification, the pinned list or the Activity log, and slow every browser showing it. Found by CodeQL and by timing worst-case messages. These now take a few milliseconds.

### 2.51.1
- **DNS-rebinding bypass of the link-preview protection.** A website's address was checked once, then looked up again when connecting, so a hostile DNS server could answer "public" the first time and "internal" the second. The connection now uses the exact address that was checked.
- **Decompression bomb in backup restore.** A tiny uploaded backup file could claim to unpack to a huge size, or a huge number of files, and fill the disk. Backups are now checked before anything is unpacked.
- **Messages could be stored under a channel that doesn't exist**, by sending them directly to the server. The channel is now checked.
- **The backup download could be triggered by a link from another website (CSRF).** It now requires a form submission from the admin panel itself.
- **Added the `X-Content-Type-Options: nosniff` header** to every response.

### 2.45.1
- **Link previews could be redirected to internal services (SSRF).** An outside website could redirect the preview fetch to Home Assistant's own API or another internal address and have its contents shown in the chat. Every redirect is now checked the same way the original link is.
- **Stored cross-site scripting (XSS) through an image's file address.** A crafted file address could break out of the image's click handler and run code in the browser of anyone who clicked the image.
- **Fake attachments.** A message sent directly to the server could claim any outside link was a file shared in the chat, which could disguise a phishing link as a family member's upload. File messages must now point to a file this server actually stored.
- **Reactions could be faked or removed for someone else** by setting your display name to theirs. Reactions now use each person's Home Assistant account instead of their display name.

### 2.42.1
- **The "Welcome to #channel" heading inserted the channel name without escaping it** (found by CodeQL). Channel names can only contain letters, numbers and dashes, so this wasn't exploitable, but it's escaped now.

### 2.32.3
- **The AppArmor profile, added in 2.29.0, now runs in enforcing mode.** Anything outside the app's allowed files and network access is blocked, not just logged.

### 2.21.11
- **Open redirect through the `X-Ingress-Path` header** (found by CodeQL). Addresses starting with `//`, which browsers treat as a different website, got past the old check. Anything with a scheme, a host or a leading `//` is now rejected.

### 2.21.10
- **The session signing key file was readable by other users on the system.** It is now readable only by the app (`0600`), including on existing installs.

### 2.21.9
- **Updated Flask to 3.1.3** for an issue that could let a caching proxy serve one person's page to someone else. Not exploitable here, because the app already turns caching off, but updated anyway.

### 2.21.8
- **Updated python-socketio to 5.16.2** for two issues: a remote code execution bug that doesn't apply to how this app runs, and a memory-exhaustion attack where a client could make the server hold half-sent messages forever.

### 2.19.0
A full security review of the app.
- **CVE-2025-58068: HTTP request smuggling in eventlet**, the web server the app runs on. Request smuggling could defeat the way Home Assistant passes along who is logged in. Updated eventlet to 0.40.3.
- **The push-notification device name could steer a request elsewhere in Home Assistant's API.** It was used, unchecked, to build a request made with the app's own Home Assistant access. It now must be a plain device name.
- **The `max_file_size` setting wasn't enforced**; every upload was allowed up to 100MB. The configured limit now applies.
- **The upload routes didn't check who was uploading**, unlike the rest of the app. They do now.
- **No limit on admin password attempts.** The admin login now locks for 5 minutes after 10 failed attempts.
- **The custom emoji upload didn't clean up its file name.** It wasn't exploitable, but it now uses the same safe file naming as other uploads.
- **No server-side limit on message length.** Messages are now capped (currently 20,000 characters).
- **Session cookie protections** (`HttpOnly`, `SameSite=Lax`) are now set explicitly instead of relying on Flask's defaults.
- **A one-letter avatar initial wasn't escaped.** A single character can't form an HTML tag, so this wasn't exploitable, but it's escaped now.

### 2.1.0
- **Stored cross-site scripting (XSS).** Reaction emoji, file names and custom emoji names were put into the page without escaping, so a crafted value could run code in every family member's browser. All of these are escaped now, and file and emoji addresses can no longer use `javascript:` links.
- **Anyone could send messages as someone else** by changing the sender name the browser sent. The server now decides who sent a message, reaction or upload from the Home Assistant login.
- **The session signing key was hard-coded** in the source code. It's now randomly generated for each install and kept across restarts.
- **The `X-Ingress-Path` header could be used for an open redirect.** A first check was added here and made stricter in 2.21.11.
