# Family Chat

A private, Discord-like chat application for your family that runs entirely inside [Home Assistant](https://www.home-assistant.io/). No separate accounts to create, no ads, no data mining — just a simple, secure messaging platform where your family can chat, share files, react with emojis, and stay connected.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://www.home-assistant.io/)

![Family Chat Screenshot](https://private-user-images.githubusercontent.com/190531648/639602377-d5abe812-c1d3-480c-b479-165295354edd.png)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Permissions & Roles](#permissions--roles)
- [Security](#security)
- [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)
- [Changelog](#changelog)
- [License](#license)
- [Support](#support)

---

## Overview

Family Chat is a Home Assistant add-on that provides a self-hosted, real-time messaging platform for families. It automatically authenticates users through Home Assistant's ingress system — when a family member opens the chat from the Home Assistant sidebar, they're instantly signed in as themselves with no additional login required.

**Key Principles:**
- **Privacy First**: All data stays on your Home Assistant instance
- **No External Dependencies**: No cloud services required (except optional GIPHY)
- **Simple & Familiar**: Uses an interface that's intuitive for all ages
- **Self-Hosted**: You own your data, stored locally in SQLite

---

## Features

### Messaging
| Feature | Description |
|---------|-------------|
| **Real-time Chat** | Messages appear instantly via WebSockets — no refresh needed |
| **Channels** | Organize conversations into topic-based channels (e.g., `#general`, `#memories`, `#plans`) |
| **Channel Categories** | Group channels under collapsible category headers (Discord-style) |
| **Message Replies** | Reply to specific messages with quoted context |
| **@Mentions** | Mention family members with `@` — they'll get notified even if they haven't subscribed to the channel |
| **Unread Indicators** | Bold channel names show new activity; red badges show @mentions |
| **Search** | Search across all channels for message history |
| **Link Previews** | Automatic preview cards for shared URLs (with SSRF protection) There is a slight delay when processing the link previews for security purposes. |
| **Message History** | Infinite scroll to load older messages (cursor-based pagination) |

### Media & Files
| Feature | Description |
|---------|-------------|
| **File Sharing** | Upload images, videos, documents, and more (configurable file types) |
| **Screenshot Paste** | Paste screenshots directly from clipboard (Ctrl+V / Cmd+V) |
| **GIF Picker** | Search and post GIFs from GIPHY (requires free API key) |
| **Custom Emoji** | Upload your own emoji for family inside jokes |
| **Avatar Upload** | Personalize your profile with a custom photo (with circular crop tool) |
| **Image Previews** | Inline previews for uploaded images |

### Calendar Integration
| Feature | Description |
|---------|-------------|
| **Home Assistant Calendar** | View upcoming events from all your HA calendars. The server admin can choose which calendars can be used for this. |
| **Add Events** | Create calendar events directly from chat discussions |
| **Event Details** | Click any event to see full details (date, time, location, description) |
| **Admin Controls** | Restrict which calendars can receive new events |

### Notifications
| Feature | Description |
|---------|-------------|
| **Push Notifications** | Get notified on your phone via Home Assistant Companion App |
| **Per-Channel Subscriptions** | Choose which channels notify you |
| **@Mention Alerts** | Always notified when mentioned, regardless of subscription |

### Customization
| Feature | Description |
|---------|-------------|
| **Display Names** | Set a custom name separate from your Home Assistant username |
| **Light/Dark Theme** | Choose your preferred color scheme |
| **Custom Chat Name** | Rebrand the chat to match your family name |
| **Collapsible Sidebars** | Hide channel list or member list for more space |

### Administration
| Feature | Description |
|---------|-------------|
| **Admin Panel** | Password-protected panel for server management |
| **Channel Management** | Add, delete, and reorder channels and categories |
| **User Management** | Set display names for family members |
| **Server Owner** | Designate an owner with elevated privileges |
| **Calendar Restrictions** | Control which calendars can receive events |

---

## Architecture

### Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.11 + Flask |
| **WebSocket** | Flask-SocketIO with Eventlet |
| **Database** | SQLite (persistent storage in `/data`) |
| **Frontend** | Vanilla JavaScript + Custom CSS |
| **Container** | Docker (Alpine Linux 3.19 base) |
| **Security** | Custom AppArmor profile |

### Project Structure

```text
family-chat/
├── app/
│   ├── server.py           # Flask/SocketIO application
│   ├── requirements.txt    # Python dependencies
│   ├── static/             # CSS, JavaScript, assets
│   └── templates/          # HTML templates
├── config.yaml             # Add-on configuration schema
├── Dockerfile              # Container build instructions
├── apparmor.txt            # Security profile
└── run.sh                  # Container entrypoint
```

### Key Dependencies

- **Flask ≥3.1.3** — Web framework
- **Flask-SocketIO ≥5.6.1** — Real-time WebSocket communication
- **Eventlet ≥0.40.3** — WSGI server with WebSocket support
- **Python-SocketIO ≥5.16.2** — Socket.IO protocol implementation

---

## Installation

### Method 1: Add-on Store (Recommended)

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**
2. Click the **⋮** menu → **Repositories**
3. Add this repository URL: `https://github.com/Arbitrary8481/family-chat`
4. Find **Family Chat** in the store and click **Install**
5. Configure the `admin_password` (see [Configuration](#configuration))
6. Click **Start**

### Method 2: Manual Build

# Clone the repository
git clone https://github.com/Arbitrary8481/family-chat.git

# Copy to your Home Assistant add-ons directory
cp -r family-chat/family-chat /addons/

# Install from local add-ons in the Home Assistant UI

> **Important**: After installation or updates, perform a **Rebuild** (not just Restart) if certain features aren't working — some permissions require a full rebuild to take effect.

---

## Configuration

Configure via the **Configuration** tab in the add-on settings:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `theme` | `dark` \| `light` | `dark` | UI color scheme |
| `max_file_size` | int (1-100) | `25` | Maximum upload size in MB |
| `admin_password` | password | `changeme` | **Required**: Password for admin panel |
| `giphy_api_key` | password | `""` | Optional: Enables GIF picker |
| `allowed_file_types` | list | `[image/*, video/*, audio/*, application/pdf, text/*]` | Permitted MIME types |

> **Note**: Change the default `admin_password` immediately — `changeme` is not secure!

### Getting a GIPHY API Key (Optional)

1. Visit [developers.giphy.com](https://developers.giphy.com/)
2. Create a free account and app
3. Copy the API key to the `giphy_api_key` field

---

## Permissions & Roles

Family Chat has a three-tier permission system:

### Everyone (All Users)

- Send messages and reactions
- Create channels
- Upload custom emoji
- Set personal display name
- Manage notification subscriptions
- Delete own messages

### Admin

- Access admin panel (`/admin`) with password
- Delete any channel
- Rename the chat
- Manage everyone's display names
- Restrict calendar access
- Designate server owner
- Delete any message

### Server Owner

- All admin powers tied to Home Assistant login
- No admin password required day-to-day
- Can delete channels from Settings panel

> **Note**: Currently, all users need Home Assistant admin access to use the add-on due to Home Assistant's permission model for ingress-based add-ons. This doesn't give them admin access on the chat server. Once they change the permissions model I will see what I can do to resolve this.

---

## Security

Family Chat takes security seriously:

- **Custom AppArmor Profile**: Container is restricted to only necessary filesystem and network access
- **SSRF Protection**: Link previews validate resolved IPs to prevent internal network probing
- **Input Validation**: All user inputs are sanitized and validated server-side
- **Session Security**: HttpOnly cookies with SameSite=Lax protection
- **Brute-force Protection**: Admin panel locks after 10 failed attempts (5 minutes)
- **No External Exposure**: Only accessible through Home Assistant ingress (no direct port mapping)
- **File Upload Security**: Filename sanitization, type validation, and size limits
- **XSS Prevention**: All dynamic content is HTML-escaped

See [SECURITY.md](SECURITY.md) for vulnerability reporting.

---

## Requirements

### Required

- Home Assistant with Supervisor (Home Assistant OS or Supervised)
- Home Assistant admin access for all users

### Optional

- **GIPHY API Key** — for GIF search functionality
- **Home Assistant Companion App** — for push notifications on mobile devices

### Architecture Support

- ✅ `amd64` (x86_64)
- ✅ `aarch64` (ARM64)
- ❌ `armv7` and other 32-bit architectures (deprecated by Home Assistant)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Add-on won't start** | Check the add-on log: Settings → Add-ons → Family Chat → Log |
| **New features missing** | Perform a **Rebuild** (not just Restart) |
| **Notifications not working** | Ensure Companion App is installed and `homeassistant_api` permission is granted |
| **GIF picker missing** | Add a GIPHY API key in configuration |
| **Avatar not updating** | Hard refresh the page (Ctrl+Shift+R) |
| **Mobile sidebar issues** | Tap the ✕ button or dimmed backdrop to close |

### Debug Logs

Enable detailed logging by checking the add-on logs after reproducing an issue. The app logs explicitly when:

- Notifications are sent (or skipped)
- API errors occur
- Authentication issues happen

---

## Changelog

See [CHANGELOG.md](family-chat/CHANGELOG.md) for detailed version history.

**Recent Highlights:**

- **v2.36.0** — Link previews with SSRF protection
- **v2.35.0** — Infinite scroll message history
- **v2.34.0** — Message replies with quoted context
- **v2.31.0** — Channel categories
- **v2.27.0** — @mention badges and notifications
- **v2.26.0** — @mentions system
- **v2.23.0** — Calendar event creation
- **v2.22.0** — Avatar uploads with cropper

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Support

This is a self-hosted, family-run project. There is no formal support channel.

- **Bugs/Issues**: Check the add-on logs first, then report any errors via a GitHub issue.
- **Feature Requests**: Open a GitHub issue or submit a pull request.
- **Donations**: [Buy me a coffee](https://ko-fi.com/arbitrary8481) ☕

---

## About This Project

Family Chat was built for personal use and is maintained according to the author's preferences. AI-assisted tools have been used in development and will continue to be used where helpful. If this approach doesn't align with your preferences, you're welcome to fork or build an alternative.

**Data Storage**: All messages, files, and user data are stored locally on your Home Assistant instance. Ensure you have adequate storage space for images and files shared by your family.
