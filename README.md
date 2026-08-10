# Family Chat

A private, Discord-style chat for your family that runs entirely inside Home Assistant. There's no separate account to create — Family Chat signs everyone in automatically using whoever's already logged into Home Assistant, so each person just shows up as themselves.

## Features

**Channels** — Organize conversations into channels (e.g. `#general`, `#memories`, `#plans`). Anyone can add a new channel from their own Settings; removing one is restricted to an admin or the server owner, since it affects everyone at once.

**Real-time messaging** — Messages, reactions, and deletions all show up instantly for everyone in that channel via WebSockets, without needing to refresh.

**Reactions** — React to any message with a full emoji picker (search by keyword, browse by category, or use your recently-used emoji), including your own custom uploaded emoji. Clicking a reaction again removes it.

**GIFs** — Search GIPHY or browse what's trending and post a GIF straight to the chat, no downloading required. Requires a free GIPHY API key (see Configuration below).

**Custom emoji** — Upload your own emoji from Settings and use them anywhere the regular emoji picker appears.

**File & screenshot sharing** — Attach a file with the 📎 button, or just paste a screenshot straight from your clipboard (Ctrl+V / Cmd+V) — no need to save it to disk first.

**Clickable links** — URLs posted in a message become real, clickable links automatically.

**Search** — Search message history across every channel at once, not just the one you're currently viewing.

**Delete messages** — Delete your own messages any time. Admins and the server owner can delete anyone's.

**Push notifications** — Opt in (per channel) to get notified on your phone when a new message comes in, using Home Assistant's own notification system — specifically the Home Assistant Companion App. No separate push service, no extra accounts; just pick which of your devices to notify from Settings.

**Personal display names** — Set your own display name (independent of your Home Assistant username) from Settings. An admin can also set or override anyone's from the admin panel.

**Jump to the latest messages** — Scroll up to read history without getting yanked back down every time someone posts — a small button appears (with an unread count) to jump back to the bottom whenever you want.

**Light or dark theme, configurable chat name** — Rebrand the chat's name/icon (shown in the upper-left) from the admin panel to whatever your family calls it.

## Permissions

- **Everyone** (anyone signed into Home Assistant) can chat, react, add channels, upload custom emoji, set their own display name, and manage their own notification subscriptions.
- **Admin** — a separate password (set in the add-on configuration) unlocks the admin panel: rename the chat, delete channels, manage everyone's display names, and designate a server owner.
- **Server Owner** — an admin can designate one Home Assistant account as the owner, from the admin panel. The owner gets the same message- and channel-deletion powers an admin has, but tied to their own Home Assistant login — no admin password needed day-to-day.

## Requirements

- Home Assistant with Supervisor (required for ingress and for the add-on's access to Home Assistant's notification services).
- To post GIFs: a free [GIPHY API key](https://developers.giphy.com/).
- To receive push notifications: the [Home Assistant Companion App](https://www.home-assistant.io/companion-app/) installed and connected on the devices you want notified.

## Installation

1. Add this repository to your Home Assistant add-on store and install **Family Chat**, or build it locally from this repo.
2. Open the add-on's **Configuration** tab and set an `admin_password` (see below) — it defaults to `changeme`, which is not a real password.
3. Start the add-on and open it from the Home Assistant sidebar.

Some features (channel add/delete permissions, notifications) rely on add-on permissions that are only picked up on a full **Rebuild**, not a simple **Restart** — if something added in a newer version doesn't seem to be there yet, rebuild the add-on once.

## Configuration

| Option | Description |
|---|---|
| `theme` | `dark` or `light`. |
| `max_file_size` | Maximum upload size, in MB. |
| `admin_password` | Password for the admin panel (`/admin`). Change this from the default. |
| `giphy_api_key` | Optional. Enables the GIF picker when set; the picker is hidden until it's configured. |
| `allowed_file_types` | MIME type patterns permitted for uploads (e.g. `image/*`, `application/pdf`). |

Everything else — the chat's display name, channels, the server owner, and individual display names — is configured from within the app itself (the admin panel, or each person's own Settings), not from this options screen.

## Support

This is a self-hosted, family-run project. I will work on it when I can. If you find an issue, open an issue here on GitHub and I will see what I can do.
