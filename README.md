# Family Chat

A private chat for your family that runs entirely inside Home Assistant. There's no separate account to create — Family Chat signs everyone in automatically using whoever's already logged into Home Assistant, so each person just shows up as themselves. There are no ads, the data is all hosted on your Home Assistant system (make sure you have room for all those gifs and images your family posts) and no monetization being forced down your throat.
<img width="1494" height="675" alt="screenshot - FC" src="https://github.com/user-attachments/assets/d5abe812-c1d3-480c-b479-165295354edd" />
## Features

**Channels** — Organize conversations into channels (e.g. `#general`, `#memories`, `#plans`). Anyone can add a new channel from their own Settings; removing one is restricted to an admin or the server owner, since it affects everyone at once.

**Real-time messaging** — Messages, reactions, and deletions all show up instantly for everyone in that channel via WebSockets, without needing to refresh.

**Reactions** — React to any message with a full emoji picker (search by keyword, browse by category, or use your recently-used emoji), including your own custom uploaded emoji. Clicking a reaction again removes it.

**GIFs** — Search GIPHY or browse what's trending and post a GIF straight to the chat, no downloading required. Requires a free GIPHY API key (see Configuration below).

**Custom emoji** — Upload your own emoji from Settings and use them anywhere the regular emoji picker appears.

**Calendar integration** - Integrates directly with your home assistant calendar. However if you have more than one you can control which calendars it displays from the admin panel. Want to add a calendar item from a discussion with the family? Just click the calendar button in the messaging interface to do so!

**File & screenshot sharing** — Attach a file with the 📎 button, or just paste a screenshot straight from your clipboard (Ctrl+V / Cmd+V) — no need to save it to disk first.

**Clickable links** — URLs posted in a message become real, clickable links automatically.

**Search** — Search message history across every channel at once, not just the one you're currently viewing.

**Delete messages** — Delete your own messages any time. Admins and the server owner can delete anyone's.

**Push notifications** — Each user can opt in (per channel) to get notified on your phone when a new message comes in, using Home Assistant's own notification system — specifically the Home Assistant Companion App. No separate push service, no extra accounts; just pick which of your devices to notify from Settings. To be clear, this means you can use any currently configured notification system you have set up.

**Personal display names** — Set your own display name (independent of your Home Assistant username) from Settings. An admin can also set or override anyone's from the admin panel.

**Jump to the latest messages** — Scroll up to read history without getting yanked back down every time someone posts — a small button appears (with an unread count) to jump back to the bottom whenever you want.

**Light or dark theme, configurable chat name** — Rebrand the chat's name/icon (shown in the upper-left) from the admin panel to whatever your family calls it.

## Permissions

Everyone who can open this add-on at all is, by necessity, a Home Assistant admin — see Requirements below for why. Within the app itself, though, there's a separate, much narrower set of roles:

- **Everyone** (anyone signed into Home Assistant) can chat, react, add channels, upload custom emoji, set their own display name, and manage their own notification subscriptions.
- **Admin** — a separate password (set in the add-on configuration) unlocks the admin panel: rename the chat, delete channels, manage everyone's display names, restrict which calendars can be added to, and designate a server owner.
- **Server Owner** — an admin can designate one Home Assistant account as the owner, from the admin panel. The owner gets the same message- and channel-deletion powers an admin has, but tied to their own Home Assistant login — no admin password needed day-to-day.

## Security

Ships with a custom [AppArmor](https://developers.home-assistant.io/docs/apps/presentation/) profile (`apparmor.txt`) scoping the container down to only what it actually needs — its own code, `/data` for the database and uploads, and network access, nothing else. Verified against a real instance across every distinct feature this app has (chat, uploads, avatars, the admin panel, calendar events, GIFs) and now runs in full enforcing mode, not just logging — see the comments at the top of the file for the verification history.

## Requirements

- **Every family member needs Home Assistant admin access.** Home Assistant doesn't currently support granting a non-admin user access to just one specific add-on — ingress-based add-ons like this one are only reachable by admin accounts, full stop. This isn't something this add-on chose; it's a limitation of Home Assistant's permission model today. If Home Assistant adds more granular, per-add-on permissions for non-admin users in the future, this requirement should be able to relax to match.
- Home Assistant with Supervisor (required for ingress and for the add-on's access to Home Assistant's notification services).
- To post GIFs: a free [GIPHY API key](https://developers.giphy.com/).
- To receive push notifications: the [Home Assistant Companion App](https://www.home-assistant.io/companion-app/) installed and connected on the devices you want notified.

## Installation

1. Add this repository to your Home Assistant add-on store and install **Family Chat**, or build it locally from this repo.
2. Open the add-on's **Configuration** tab and set an `admin_password` (see below) — it defaults to `changeme`, which is not a real password.
3. Start the add-on and open it from the Home Assistant sidebar.

Some features (channel add/delete permissions, notifications) rely on add-on permissions that are only picked up on a full **Rebuild**, not a simple **Restart** — if something added in a newer version doesn't seem to be there yet, rebuild the add-on once.

## Configuration

| Option               | Description                                                                            |
| -------------------- | -------------------------------------------------------------------------------------- |
| `theme`              | `dark` or `light`.                                                                     |
| `max_file_size`      | Maximum upload size, in MB.                                                            |
| `admin_password`     | Password for the admin panel (`/admin`). Change this from the default.                 |
| `giphy_api_key`      | Optional. Enables the GIF picker when set; the picker is hidden until it's configured. |
| `allowed_file_types` | MIME type patterns permitted for uploads (e.g. `image/*`, `application/pdf`).          |

Everything else — the chat's display name, channels, the server owner, and individual display names — is configured from within the app itself (the admin panel, or each person's own Settings), not from this options screen.

## Support

This is a self-hosted, family-run project — there's no formal support channel. Check the add-on log (Settings → Add-ons → Family Chat → Log) if something isn't working as expected; several of the trickier bugs found so far have left a clear trace there.

## Note:

AI-assisted tools have been used in this project and will continue to be used where I find them useful. This project is built for my own needs and use cases, and I maintain it according to my own preferences.

You are welcome to use it if it works for you, but I will not change the project's development approach to accommodate objections to the use of AI tools. I believe these tools can be genuinely useful when used appropriately. If the use of AI-assisted tools is a deal-breaker for you, this project may simply not be the right fit. You are, of course, free to use or build an alternative that better matches your preferences.

## Kindness

I didn't do this for the money, thus the MIT license. However if you really want to buy me a coffee to thank me for this, you can do so here: [Buy me a coffee](https://ko-fi.com/arbitrary8481)
