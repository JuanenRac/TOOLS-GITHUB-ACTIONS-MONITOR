<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Tabs of the page

Generated from the page. The same data is in the endpoints; an AI does not need the page.

- `al`: Alerts (every sentinel in one list, silences)
- `cfg`: Settings (tabs Basic, General ... AI, Quota ...)
- `charts`: Charts and history
- `fleet`: Fleet (hundreds of repositories grouped and paged; address #fleet)
- `hist`: History of runs
- `interface`: Interface
- `les`: Lessons (lessons from the failures; address #lessons)
- `now`: Right now (runs, one row per repository)
- `rep`: Reports (the optional reports; address #reports)
- `repos`: Repositories
- `sci`: CI sentinel (panels A1-A13 and the lint of the workflows; address #sentinel-ci; only while sentinel.enabled is on)
- `scol`: Collab sentinel (issues and pull requests; address #sentinel-collab; only while sentinels.collab.enabled is on)
- `sent`: Summary of the sentinels (report and trends; address #sentinel; present while any sentinel is on)
- `ssec`: Security sentinel (what GitHub says is open or missing; address #sentinel-security; only while sentinels.security.enabled is on)
- `team`: Team (health of the repositories ranked by risk, with filters and the detail of each)
- `trep`: Scheduled reports (the files written on a schedule; address #team-reports)

Screens: `/screen/1` to `/screen/3` show the tabs chosen in `ui.screenN_tabs`.
