<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Roles and permissions

Generated from the code. Team mode only (`auth.enabled`); without it one person uses the monitor with no login.

- Roles, from least to most: `viewer`, `maintainer`, `admin`.
- Every GET needs `viewer`, except `/api/run-log`, `/api/github-token`, `/api/advanced`, `/api/github-app/status`, `/api/auth/users`, `/api/auth/audit` (`admin`).
- A POST needs `maintainer` only for: `/api/alerts/mute`, `/api/alerts/unmute`, `/api/ai/ack`, `/api/hot-only`, `/api/mode`, `/api/refresh-repos`, `/api/sentinel/parte/save`, `/api/discovery/group`, `/api/welcome`, `/api/session-token`. Every other POST needs `admin`.
- Public (no session): `/api/auth/login`, `/api/auth/me`, `/api/auth/bootstrap`, `/api/auth/logout`, `/api/health`, `/api/webhook`, `/api/access`, `/login`.
- Writing a lesson needs `lessons.allow_write` on, an `admin`, and a confirmation; the MCP server needs `--allow-lessons` too.
