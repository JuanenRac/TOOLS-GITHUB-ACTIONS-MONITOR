<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SCREENS_spa.md) | [🇫🇷 Français](SCREENS_fra.md) | [🇮🇹 Italiano](SCREENS_ita.md) | [🇩🇪 Deutsch](SCREENS_deu.md) | [🇨🇳 简体中文](SCREENS_zho.md) | [🇯🇵 日本語](SCREENS_jpn.md) | [🇵🇹 Português](SCREENS_por.md)

# Screens, sizes and orientation

The page adapts to the size of its window, from a phone to 4K, upright or turned, and one monitor can serve several screens, each one showing the tabs you choose. Nothing is polled twice: every screen reads the same state.


For a TV or a wall with larger type, a high contrast or a rotation through a few tabs, see [KIOSK.md](KIOSK.md).
## Addresses

- `/` - the whole page.
- `/screen/1`, `/screen/2`, `/screen/3` - the tabs set for that screen (`ui.screen1_tabs` ...). Open each one in a window of its own monitor or TV.
- `?orient=portrait` or `?orient=landscape` forces the layout of one window; `?tabs=now,charts` and `?rotate=30` set the tabs and the seconds between them for one window.

## Settings

| Setting | What it does |
|---|---|
| `ui.orientation` | auto follows the window; portrait stacks the panels in one column; landscape keeps the side-by-side layout. |
| `ui.rotate_seconds` | 0 = off. Seconds between the tabs of a screen that has more than one. |
| `ui.screen1_tabs` | Tabs of /screen/1, comma separated: now, al, charts, sent, sci, scol, ssec, team, fleet, repos, rep, trep, les, hist, cfg. Empty = all. |
| `ui.screen1_orientation` | auto, portrait or landscape for /screen/1 only. |
| `ui.screen2_tabs` | Tabs of /screen/2. |
| `ui.screen2_orientation` | Orientation of /screen/2. |
| `ui.screen3_tabs` | Tabs of /screen/3. |
| `ui.screen3_orientation` | Orientation of /screen/3. |
| `ui.now_sort` | Order of Happening now for who has not chosen one: ecosystem, severity, age, newest, repo, event or state. |
| `ui.alerts_sort` | Order of the Alerts tab for who has not chosen: server, severity, streak, class, age, newest, repo, origin or state. |
| `ui.remember_folds` | Remember what is folded: on (the default), the sections folded or unfolded by hand stay so after a refresh and when the page is opened again; off, only while the page stays open. |

## Order of the lists

The section **Happening now** of the first tab is sorted by ecosystem, with a heading for each one. The list above the section changes it: ecosystem, severity (stuck first, then runs with a failed job, then running, then queued), age (longest running first), newest first, repository, trigger (push, pull_request, schedule...) and state (running before queued). The choice is remembered for each person: in the team mode the server keeps it with the user (`GET` and `POST /api/auth/me/view`, so it follows the user to another browser), otherwise this browser does. Until someone chooses, the order is `ui.now_sort` of the configuration file (ecosystem when it is missing or wrong). The buttons **Expand all** and **Collapse all** next to the list unfold or fold every repository of the section at once, in any order, and the choice is remembered for each person in the same place and survives a refresh (a repository you open or close by hand afterwards keeps your choice).

The list of the **Alerts** tab keeps the order the monitor sends unless a person chooses another with the list above it: severity (critical, error, warning, info), the longest streak of failures in a row first, class (an error or critical alert is real and goes before the ones to watch), the oldest first, the newest first, repository, origin (the sentinel that raised it) and state (open before silenced). It is remembered the same way, and until someone chooses, `ui.alerts_sort` of the configuration file applies (`server` when it is missing or wrong).

**Folded and unfolded sections** stay as the person left them. The sections of the CI sentinel, the cards of the other sentinels, the lists of notices of the first tab and the versions of the updater are drawn again at every refresh, and a refresh never opens again what was folded nor folds what was unfolded: each block has a stable name and the page keeps the choice of each one, in memory and, with `ui.remember_folds` on (the default), in the browser too. Only a click of the person records a choice; what the page opens by itself (the first card with alerts of a sentinel that nobody has touched yet) is not taken for one.

## Sizes tested

A browser test opens the page in each of these sizes, goes through every tab and fails on a sideways scroll or a text that leaves its box. Windows of 2400 px or more get a larger type (and 3200 px a larger one still) instead of a stretched layout; a window taller than wide stacks the panels.

| Size | Kind |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## Recipe for a desk with two or three screens

1. On the computer that runs the monitor, set `ui.screen1_tabs` to `now,al`, `ui.screen2_tabs` to `charts,repos` and, for a turned monitor, `ui.screen2_orientation` to `portrait`.
2. Open `http://this-computer:8765/screen/1` in a window on the first monitor and `/screen/2` on the second; press F11 for full screen. From another computer, use the network mode with its access token.
3. For a wall screen nobody touches, give it several tabs and set `ui.rotate_seconds` to 20-30.

## Wall screens: overview, right now and sentinels

Three pages for a monitor or a TV that nobody touches. They have no side menu and no navigation, show everything in one view with big type, animate what is alive and make failures blink softly. They only read: no button changes anything, and they never call GitHub (they show what the monitor already holds).

| Address | What it shows |
|---|---|
| `/screen/overview` | Score ring and letter; the fleet (green, red, stuck, waiting); the last 24 hours and 7 days as area charts; a heat map of repositories by hour; what has been red the longest; runners and minutes; the latest events; the GitHub allowance as a gauge. The fleet card also shows the map by groups: one bar for each group of the Fleet view (the same grouping, `fleet.group_by`) with its repositories that are red, need attention, are in order or have no data; only the name of the group and numbers. |
| `/screen/fleet` | Every repository of the fleet by group (the grouping and the order of the Fleet tab, the riskiest group first): a small square for each healthy repository and a chip with the name for each one that needs a look, with the totals of the fleet on top. What does not fit is counted ("+3 more"). |
| `/screen/now` | What is happening this minute: running runs with progress and duration, the queue, runs waiting for approval, recent failures, merges and releases, releases due and a live line of the last two hours. |
| `/screen/sentinels` | One card for each sentinel (A1 to A12) with its level, open findings, whether its sources can be read, the last sweep and a ring that follows the sweep; an animated radar that marks what is wrong and the alerts by severity. |

### Parameters of the address

One address for each monitor. A parameter can make a window quieter or smaller than the settings allow, never louder.

| Parameter | Effect |
|---|---|
| `?monitor=1` to `9` | The number shown next to the title. |
| `?theme=light` (or `dark`, `auto`, `contrast`, or the name of one of the sixteen themes) | Colours of the whole window, over what the settings say. `contrast` is white on black, for a screen seen from far away. |
| `?density=compact`, `normal` or `large` | Size of the type. `?scale=1.5` enlarges everything (0.5 to 3). |
| `?refresh=10` | Seconds between updates (5 to 120). |
| `?lang=de` | Language (en, es, de, fr, it, ja, zh, pt). |
| `?rotate=30` | The window turns by itself through overview, right now and sentinels every 30 seconds (at least 5; 0 = it stays on one screen). With `screens.mode` = rotate it already turns; this changes the pace of one window. |
| `?jump=off` | Only with `screens.mode` = rotate: the window turns but never jumps to a new red. |
| `?blink=off` | Failures keep a fixed glow instead of blinking. It cannot turn on what `screens.blink` keeps off. |
| `?repo=WORD,WORD` | Only the repositories whose name holds one of the words (letters, digits and `. _ - /`, up to eight words). `/screen/overview` and `/screen/now` keep only the repositories whose name the screen shows (a hidden name is never matched), the figures follow the rows that are kept, and the score and the map of groups, which belong to the whole fleet, are not shown; `/screen/sentinels` is not filtered. |
| `?sound=on` | A short beep for a new failure, only if `screens.sound` allows it. Off by default. |
| `?safe=4` | Keeps the content this many percent (0 to 10) away from each edge of the window, for a television that cuts the border (overscan). It replaces `screens.safe_margin_percent` for this window. |

### Language of the screens

The language of a screen is decided in this order: `?lang=xx` in the address; then the language chosen on the main page of the same browser (it is saved there, and a screen opened in that browser reads it, so a screen follows the page without any parameter); then the language of the monitor (`MONITOR_LANG`, or the configured one). A screen whose saved language differs from the one it was served in reloads once, before it draws, with `?lang=` added and the other parameters (`?rotate=` among them) kept. The eight languages (en, es, de, fr, it, ja, zh, pt) are the same ones of the page: titles, labels, states, severities, units and the relative times ("5 min ago") come from the catalogue, and the time, the date and the numbers are written with the locale of the language (en-GB, es-ES, de-DE, fr-FR, it-IT, ja-JP, zh-CN, pt-PT). The link "Open screen" of Settings already carries `?lang=` with the language of the page. A computer that does not choose a language by itself keeps English: the language of the browser does not decide.

### Settings of the wall screens

| Setting | What it does |
|---|---|
| `screens.enabled` | Turns the three pages on. Off: `/screen/overview`, `/screen/now`, `/screen/sentinels` and `/api/screens/data` answer 404 (`/screen/1` to `/screen/3` are the page itself and do not depend on it). The lite edition serves the wall screens too, with the sentinel screen empty. Off by default. |
| `screens.default_theme` | inherit (default: the theme chosen for the whole product, see below), auto, light, dark, one of the sixteen themes or contrast. |
| `screens.default_density` | compact, normal (default) or large. |
| `screens.refresh_seconds` | Seconds between updates of a window (10 by default). The pages read the monitor, never GitHub, so a short time costs no allowance. |
| `screens.rotate_seconds` | Only with `screens.mode` = three. 0 (default) = no rotation; above 5, one window turns through the three pages. |
| `screens.blink` | Failures blink softly (on by default). |
| `screens.blink_calm_minutes` | Minutes after which a failure that nobody attended to keeps a fixed glow instead of blinking (30 by default; 0 = it blinks until solved). |
| `screens.sound` | A beep for a new failure (off by default). |
| `screens.burn_in_protection` | Moves everything a few pixels every minute (on by default). |
| `screens.safe_margin_percent` | Keeps the content this many percent away from each edge of the window, for a television that cuts the border (overscan): everything is drawn a little smaller. 0 (default) uses the whole window; 0 to 10. |
| `screens.night_dim` | Dims the screens between `screens.night_dim_from_hour` (22) and `screens.night_dim_to_hour` (7); off by default. |
| `screens.show_repo_names` | all, public (default: private repositories appear as private-1, private-2...) or none (every name is hidden). Use public or none for a screen that other people can see. With a list of repositories written by hand in `repos`, the visibility is read with one listing of the account every `discover_refresh_seconds`; a repository whose visibility could not be read counts as private. The numbers (private-1...) go only to the hidden repositories, in the order of an HMAC of the name with a key of the installation kept in a private file of the data folder, so they say nothing about where a repository falls among the others. |
| `screens.theme_overview`, `screens.theme_fleet`, `screens.theme_now`, `screens.theme_sentinels` | The theme of one screen: inherit (default: the one of `screens.default_theme`) or any of the themes above. |
| `screens.mode` | three (default: the three pages apart, one for each window) or rotate (one single page that turns through the three and jumps to a new red). |
| `screens.rotate_every_seconds` | In rotate mode, seconds on each screen (20 by default; 5 to 300). |
| `screens.alert_hold_seconds` | In rotate mode, seconds that a new red keeps the window on its screen (30 by default; 5 to 600), or until the red is gone. |
| `screens.logo_overview`, `screens.logo_fleet`, `screens.logo_now`, `screens.logo_sentinels` | On which screens the logo shows (only the overview by default). |
| `screens.logo_corner` | top-right (default), top-left, bottom-right or bottom-left. |
| `screens.logo_max_width`, `screens.logo_max_height` | Largest size of the logo in pixels at 1920 x 1080 (160 x 64 by default; it grows with the screen). |
| `screens.group_map` | On by default. Shows the map of the fleet by groups on the overview screen (the grouping of the Fleet view). Off: only the four tiles. |
| `screens.life` | On by default. A figure that changes flashes where it changed, a new failure sends a wave over its box and a change of state leaves a short trail. Nothing moves with the system setting for less motion. |
| `screens.glance_seconds` | Seconds that the header shows what changed in the last update, in up to three chips ("Red +1"); 3 by default, 0 = off (0 to 30). |
| `screens.transition` | How a window that turns changes from one screen to the next: fade (default), slide or none. |
| `screens.hide_healthy` | Off by default. The Fleet screen leaves out the squares of the healthy repositories; the overview leaves out the groups without red or yellow and the rows of the heat map without a failure. The totals stay. |
| `screens.idle_dim_minutes` | 0 = off (default). When nothing has changed for this many minutes and nothing is red, the screen dims to save the panel; the next change wakes it (1 to 1440). |
| `screens.min_font_px` | The smallest letter of the screens in pixels, whatever the size of the window (12 by default; 8 to 32). |
| `screens.menu` | On by default. The Screens button in the top bar. Off: the button disappears; the screens keep working at their own addresses. |
| `screens.menu_target` | new (default): a screen opens in a new window or tab; same: in the tab you are in. |
| `screens.menu_max_windows` | Most windows that a multi-monitor set opens at once (4 by default; 1 to 9). |
| `screens.menu_rotate_seconds` | Seconds per screen in the turning presets of the menu (20 by default; 5 to 300). |
| `screens.menu_tv_scale` | The `?scale=` of the TV preset (1.5 by default; 0.5 to 3). |

### Theme of the screens

Everything the monitor shows wears the theme chosen in Settings (`ui.theme`: auto, light, dark or one of the sixteen themes): the page, the wall screens and the sign-in page. Choosing a theme in the selector of the tab This browser also saves it as `ui.theme`, so a browser that never chose takes the one of the monitor. The HTML reports written to disk follow the light or dark setting of the computer that opens them.

The wall screens inherit it: `screens.default_theme` is `inherit` by default. Set it to another theme to fix the same one for all the screens, and `screens.theme_overview`, `screens.theme_now` or `screens.theme_sentinels` to give one screen its own. The address can still fix one window with `?theme=`. No screen writes a colour of its own: they all use the palettes of the theme, so a theme added to the page appears on the screens as well.

### Mode of the screens: three or rotate

`screens.mode` = three (default) keeps the three pages apart, one for each window. `screens.mode` = rotate makes every window one single screen that turns through overview, right now and sentinels every `screens.rotate_every_seconds` seconds (20 by default; 5 to 300).

A red failure makes the window jump to the screen that shows it: **Right now** for a workflow that failed, **Sentinels** for a sentinel panel that turns red. The window stays there `screens.alert_hold_seconds` seconds (30 by default; 5 to 600) or until that red is gone, whichever comes first, and then goes on turning. A red that was already shown does not make the window jump again until it changes or comes back. What is red when the window opens is only the starting point and does not make it jump. If a second red arrives while the window holds the first, it waits for its turn. To know, a window reads the other two screens in the background with the same read-only call (never GitHub). `?rotate=0` keeps one window on its screen and `?jump=off` keeps the turning without the jumps. Each screen puts on its own theme and its own logo as it comes up.

### Logo of the organization

The tab This browser of Settings has a block to upload the logo of your organization: PNG, JPEG, WebP or SVG, at most 1 MB. The monitor checks the real type by the first bytes of the file (the name and the label that came with it do not count), refuses an SVG with scripts, event handlers, links to other files or addresses or a document type, and keeps the picture in the `data/` folder of this computer as `org_logo` with its extension, never in the configuration. Only one logo exists: uploading another replaces it. The log of actions records the upload and the removal, never the file.

`screens.logo_overview`, `screens.logo_now` and `screens.logo_sentinels` choose on which wall screens it shows (only the overview by default), `screens.logo_corner` the corner (top-right by default) and `screens.logo_max_width` and `screens.logo_max_height` the largest size in pixels at 1920 x 1080 (160 x 64 by default; the logo grows with the screen). The picture is fitted inside that size without changing its shape and has a place of its own in the header or the footer, so it never covers the content. Its background stays transparent: a logo with a transparent background looks right in the light and in the dark themes.

The About panel always shows the logo of the monitor. With `ui.about_org_logo` on (off by default) it also shows this logo of your organization next to it, with an alternative text in the language of the page and a size that follows the width of the panel without deforming the picture. If no logo was uploaded, or the file cannot be read, the panel says so and nothing else changes.

### What they show and what they hide

The data come from `/api/screens/data?screen=overview` (or `now`, `sentinels`): a closed list of fields built from the last cycle, the snapshot of the sentinels, the alerts and the score. It never contains a link, a commit title, a job name, a user name or a path of this computer, and the workflow names of hidden repositories are hidden too. In the network mode the pages need the same access token as the rest of the monitor, and the answer is read only.

### What fits, and what happens when it does not

The three pages are drawn in units that follow the short side of the window, so the same layout fills the sizes below; nothing is stretched and nothing scrolls. A tool measures them with the DOM in the eight languages and with data that stress a screen (names of repositories of 90 characters, German compound words and Japanese names without spaces, the most rows the monitor can send, figures of seven digits, no data at all, a single datum, an old reading): `python tools/check_screens.py` (`--list` shows each finding, `--report FILE` writes them as JSON, `--size` and `--lang` choose what to measure, `--surface kiosk` measures the kiosk). It fails on a page that scrolls, a text or a box beyond the edge, a box whose content does not fit, a heading that ends in dots, two texts that cover each other, a type smaller than a hundredth of the short side of the window (12 px in a window of 1080 px) and rows hidden without notice.

| Size | Kind |
|---|---|
| 1920x1080 | Full HD |
| 2560x1440 | QHD |
| 3840x2160 | 4K |
| 3440x1440 | ultra-wide 21:9 |
| 5120x1440 | super ultra-wide 32:9 |
| 1080x1920 | Full HD turned |
| 2160x3840 | 4K turned |

- A name of a repository or a workflow that does not fit ends in dots and carries its full text in the `title`; a heading, a label or a figure never ends in dots: a heading takes a second line and a figure wider than its box gets a smaller type, down to a floor.
- When a list has more rows than its box holds, the most important come first (red before green, the newest first) and the last line says how many were left out ("+3 more"); nothing is hidden without that line.
- Safe margin (overscan): many televisions cut a few percent of every edge unless their picture mode is "just scan" or "pixel for pixel". `screens.safe_margin_percent` (0 by default, 0 to 10; `?safe=4` for one window) keeps the content that far from each edge by drawing everything smaller, and `kiosk.safe_margin_percent` does the same for the kiosk. Try 3 to 5 if the first letters of the clock or the border of the cards are cut.
- The smallest letter is `screens.min_font_px` (12 pixels by default): in a window so small that the layout would need a smaller type, the screens keep the letter and show fewer rows, saying how many they left out, instead of shrinking the text.

### How they behave

- Failures blink less than twice a second (never a strobe); a new failure makes a single flash; a failure nobody attended to for `screens.blink_calm_minutes` keeps a fixed glow. With the system setting for less motion, or `?blink=off`, nothing blinks and nothing moves. A failure is never shown by colour alone: it carries a symbol and a word.
- When the monitor does not answer, the page says so, dims and tries again after 5, 10, 20... seconds (up to 60).
- A screen that is always on is protected from burn-in: everything moves a few pixels every minute and the page can dim at night.
- What changes between two updates is seen: the figure flashes where it changed (`screens.life`), a new failure sends a wave over its box, and for `screens.glance_seconds` seconds a few chips in the header say what changed ("Red +1", "Running +2"). The first look of a screen only remembers; with the system setting for less motion nothing moves, but the chips still appear.
- A window that turns changes screen with a fade, a slide or a cut (`screens.transition`). A screen with nothing new for `screens.idle_dim_minutes` minutes rests (dimmed) as long as nothing is red.

### Setting up several monitors

1. Choose one address for each monitor, for example `/screen/overview?monitor=1`, `/screen/now?monitor=2` and `/screen/sentinels?monitor=3`; or open one window with `?rotate=20`.
2. Open each one in Chrome or Edge in kiosk mode: `msedge --kiosk "http://this-computer:8765/screen/now?monitor=2" --edge-kiosk-type=fullscreen` or `chrome --kiosk "http://this-computer:8765/screen/now?monitor=2"`; with `--app=ADDRESS` instead of `--kiosk` the window has no bars. Without kiosk mode, the discreet button at the foot of the page asks for full screen.
3. From another computer use the network mode: the access token of a viewer is enough, because these pages never write.

## Which tab is on which wall screen

Every tab of the page has a decision, written in the code (`TAB_DECISIONS` of `screens.py`) and checked by a test: it is shown on one of the wall screens, or it says why it is not. A tab that is shown has its data in the answer of `/api/screens/data` (the overview carries Alerts, Charts and Fleet; Right now carries Now; Sentinels carries the cards of the sentinel tabs). A tab that is not shown gives its reason:

- `people`: it names people, and a wall screen never shows a user name.
- `controls`: it is made of buttons and fields that change something, and a wall screen has none.
- `reading`: it is made to be read, compared or saved, not to be seen from far away.
- `text`: it is made of titles, causes and messages, which a wall screen never shows.

| Tab | Name | Wall screen | Reason |
|---|---|---|---|
| `now` | Now | `/screen/now` | - |
| `al` | Alerts | `/screen/overview` | - |
| `charts` | Charts | `/screen/overview` | - |
| `sent` | Summary | `/screen/sentinels` | - |
| `sci` | CI sentinel | `/screen/sentinels` | - |
| `scol` | Collab sentinel | `/screen/sentinels` | - |
| `ssec` | Security sentinel | `/screen/sentinels` | - |
| `sdel` | Delivery sentinel | `/screen/sentinels` | - |
| `ssup` | Supply chain sentinel | `/screen/sentinels` | - |
| `strend` | Daily trend | - | `reading` |
| `syvt` | Yesterday vs today | - | `reading` |
| `team` | Team health | - | `people` |
| `fleet` | Fleet | `/screen/fleet` | - |
| `repos` | Repositories | - | `controls` |
| `rep` | Reports | - | `reading` |
| `trep` | Scheduled reports | - | `reading` |
| `les` | Lessons | - | `text` |
| `hist` | History | - | `text` |
| `upd` | Updates | - | `controls` |
| `cfg` | Settings | - | `controls` |

## Screens menu

The **Screens** button in the top bar (the icon of two monitors) opens a menu with every kind of screen the monitor has, so nobody has to remember the addresses. It only navigates: it opens addresses, writes nothing and reads nothing from GitHub. It is on by default and `screens.menu` turns it off.

| Screen | Address | What it is |
|---|---|---|
| Dashboard | `/` | The whole page, for a person at a desk. `?repo=` filters the repositories. |
| Kiosk | `/?chrome=0&view=now` | One view without header, tabs or filters, for a monitor nobody touches. The view is a parameter. |
| Team view | `/?chrome=0&view=team` | The team view as a kiosk (complete edition). |
| Tab screens 1 to 3 | `/screen/1`, `/screen/2`, `/screen/3` | The tabs set for each monitor of a desk; `?tabs=`, `?orient=` and `?rotate=` change them for one window. |
| Wall screens | `/screen/overview`, `/screen/now`, `/screen/sentinels` | The three wall screens above. |
| Wall that turns | `/screen/overview?rotate=20` | One window that turns through the three and jumps to a new red. |
| TV | `/screen/overview?theme=contrast&density=large&scale=1.5&rotate=20` | The turning wall for a screen seen from far away. |
| Several monitors | one address per window | A set of windows, one per monitor (see below). |

Each card shows the parameters that address accepts (theme, density, refresh, scale, language, rotation, repository filter...), each one with its own help text, and the address that results. **Open** opens it in a new window or tab, or in the tab you are in, as `screens.menu_target` says; **Copy address** puts the full address on the clipboard to open it on another computer (no token is ever part of it: in the network mode that computer signs in as usual). The wall screens answer 404 while `screens.enabled` is off, so their cards say so instead of opening an empty page; the team view is not in the lite edition.

### Several monitors

Choose how many windows (at most `screens.menu_max_windows`), the layout (in a row, in a column or in a grid) and what each window shows (the three wall screens in turn, walls that turn by themselves, or the tab screens). **Open all windows** opens one window per monitor. In a browser with the Window Management API (Chrome and Edge ask for the permission *window management*) each window is placed on its own monitor, ordered as the layout says; with more windows than monitors they share a monitor in tiles. Without it the windows open where the browser puts them and the card lists one kiosk command per window (`msedge --kiosk ADDRESS --window-position=X,Y`) to start them by hand. The browser must allow pop-ups for the monitor's address.

The same catalogue is read by tools: `GET /api/screens/menu`, `monitor_cli.py screens [list|urls]` and the MCP tool `screens_menu`. All three are read only.

## Pictures

The tab Now in four sizes, with invented data (4K, a 21:9 monitor, a turned monitor, a phone):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![turned 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![phone 390x844](../../docs/screenshots/web_size_phone_light.png)

The three wall screens in 4K and on a turned monitor, with invented data:

![Overview 4K 3840x2160](../../docs/screenshots/web_screen_overview_4k.png)

![Overview 1080x1920](../../docs/screenshots/web_screen_overview_portrait.png)

![Right now 4K 3840x2160](../../docs/screenshots/web_screen_now_4k.png)

![Right now 1080x1920](../../docs/screenshots/web_screen_now_portrait.png)

![Sentinels 4K 3840x2160](../../docs/screenshots/web_screen_sentinels_4k.png)

![Sentinels 1080x1920](../../docs/screenshots/web_screen_sentinels_portrait.png)

The wall screens in other themes, with the logo of an organization and the window that turns by itself, with invented data:

![Overview, light theme](../../docs/screenshots/web_screen_overview_light.png)

![Overview with the logo and the theme Midnight](../../docs/screenshots/web_screen_overview_midnight.png)

![Sentinels, high contrast](../../docs/screenshots/web_screen_sentinels_contrast.png)

![The window that turns through the three screens](../../docs/screenshots/web_screen_rotate.png)
