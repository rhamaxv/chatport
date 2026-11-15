# Chatport design

Date: 2026-11-15. Status: approved in conversation, awaiting written review.

## Purpose

Chatport is a free desktop app that moves WhatsApp chats and media from an
Android phone to an iPhone that is already set up, without erasing the iPhone.
It runs on Windows, macOS and Linux. It is a graphical front end; the migration
itself is done by the `wamove` engine (GPL-3.0), used through a fork that carries
the group-chat fixes from Eduardo Dantas (dudantas).

Audience: people who are not comfortable with a terminal. Success means a person
plugs in both phones, follows eight screens, and ends with their Android chats,
groups and media visible in WhatsApp on the iPhone, with the iPhone's other apps
and data untouched, and with a working Undo if the result is wrong.

## Constraints

- License: GPL-3.0-or-later for both repositories. `LICENSE` and credits to
  alicin (wamove) and dudantas (group fixes) stay. The README is rewritten from
  scratch; the license and credits are not.
- The engine stays Python. Chatport is Python too (3.12+), so the GUI calls the
  engine in-process and gets real-time progress.
- Nothing is uploaded anywhere. The only network access is downloading Google's
  official `adb` platform-tools on first use.
- The 64-digit backup key lives only in memory and never reaches disk or logs.
- Decrypted chats, media and iPhone backups are stored in the per-OS app data
  folder and can be deleted from the final screen.

## Repositories

### `rhamaxv/wamove` (fork of `alicin/wamove`)

- Created with GitHub's fork button so upstream history stays intact.
- `main` = upstream `989b268` + dudantas branch `dudantas/windows-group-migration`
  merged (commit `5f1e3a6`).
- One addition on top: `wamove/api.py`, a thin layer that exposes each step as a
  function taking a `report(event)` callback instead of printing. The CLI keeps
  working unchanged. No migration logic changes.
- Chatport pins this fork to a commit hash in `pyproject.toml`.

### `rhamaxv/chatport`

```
chatport/
  src/chatport/
    __main__.py          entry point
    app.py               QApplication setup, theme, language, logging
    core/
      paths.py           per-OS data folder, work folder, logs
      jobs.py            one QThread worker per step; emits progress/done/error
      engine.py          calls wamove.api; maps its exceptions to ErrorCode
      errors.py          ErrorCode enum + mapping to i18n keys and actions
      state.py           which steps are done, saved as JSON in the work folder
      checks.py          live checks: adb, Android, iPhone, disk, OS services
    tools/
      adb.py             find adb on PATH or download platform-tools for this OS
      platform.py        Windows: Apple Mobile Device Service; Linux: usbmuxd
    ui/
      window.py          main window: left step rail + stacked pages
      pages/             one module per step (welcome, connect, key, copy,
                         prepare, backup, build, restore, done)
      widgets/           StepRail, ProgressCard, KeyGrid, Checklist, ErrorCard
      theme.py           QSS for light and dark, follows the OS setting
      assets/            icons (SVG), Inter font, app icon
    i18n/
      en.py, id.py       strings; English default, Indonesian available
  packaging/
    chatport.spec        PyInstaller
    icon.svg             master icon; build script renders .icns/.ico/.png
    make_icons.py
  .github/workflows/
    release.yml          build dmg / Setup.exe / AppImage on tag v*
    ci.yml               tests on three OSes
  tests/
    fake_engine.py       stand-in for wamove.api, scripted outcomes
    test_jobs.py, test_errors.py, test_state.py, test_checks.py
    test_ui_flow.py      pytest-qt: click through all eight steps with the fake
  docs/
    superpowers/specs/, screenshots/
  README.md, LICENSE (GPL-3.0), pyproject.toml
```

## Screens (8 steps)

1. **Welcome**: what happens, what stays safe, what is needed. Language switch.
2. **Connect**: live cards for Android (adb, device, authorization, WhatsApp
   backup present and its age), iPhone (trusted, name, iOS, backups encrypted,
   Find My), and this computer (free disk, adb, OS services). "Install adb"
   button downloads platform-tools with progress. Continue is enabled only when
   all cards are green.
3. **Backup key**: 16 boxes of 4 hex digits with paste support. On Continue the
   app copies the smallest `.crypt15` file from the phone and tries the typed
   key in the likely reading orders; wrong key is reported before any long copy.
4. **Copy from Android**: pulls the database, contact names and media, with
   bytes done, percent and time left. Then decrypts and shows a summary
   (chats, groups, messages, media).
5. **Prepare iPhone**: checklist with live verification where possible:
   WhatsApp installed and registered, Find My off, backup encryption off,
   Airplane mode on (manual confirm).
6. **Back up iPhone**: full backup with percent; banner when the iPhone asks
   for its passcode. Then prunes a WhatsApp-only copy.
7. **Build**: merges Android chats into the WhatsApp copy, shows one overall
   percent, then the coverage report from `report.json`: what came across, what
   was skipped (reactions, polls, call history...) in plain words.
8. **Restore**: confirmation with what will happen (iPhone restarts, home
   screen layout may reset, apps may redownload). Progress; cannot be cancelled.
9. **Done** (same step as 8 after success): checklist to verify in WhatsApp,
   Undo (restores the untouched WhatsApp copy), Delete private copies, Finish.

Every step's completion is saved; reopening the app resumes at the first
unfinished step. Going back resets later steps.

## Engine bridge

`core/jobs.py` runs exactly one job at a time on a worker QThread. Each job
calls one `wamove.api` function with a `report` callback. Events:
`progress(step, pct, eta_s, phase, data)`, `need(what)` (passcode), `done(data)`,
`error(code, data)`. Progress is throttled to ~8 updates/second. Jobs: adb
download, key check, copy, decrypt, iphone backup, build, restore, undo.

## Error handling

`core/errors.py` maps every engine exception to one `ErrorCode` (about 25:
no_adb, no_android, android_unauthorized, no_backup_on_android,
old_backup_format, key_format, key_wrong, no_space, no_iphone,
iphone_untrusted, iphone_disconnected, password_needed, find_my_on,
whatsapp_missing_on_iphone, build_failed, nothing_to_restore, usbmuxd_missing,
apple_service_missing, cancelled, unknown...). Each code has a title, a
plain-language explanation and an action button (Retry, Open guide, Copy log).
`unknown` shows the exception type and offers "Copy log"; the log never
contains the key or phone numbers.

## OS requirements and checks

- macOS 12+: nothing extra.
- Windows 10+: Apple Mobile Device Service must be running (comes with iTunes
  from the Microsoft Store). Check via `sc query` / service list; show
  instructions if missing.
- Linux: `usbmuxd` must be installed and running. Check via `which usbmuxd` and
  the socket `/var/run/usbmuxd`; show distro-specific install commands.
- All: adb. Found on PATH or downloaded to the app data folder from
  `dl.google.com/android/repository/platform-tools-latest-<os>.zip`.

## Packaging and release

- PyInstaller one-folder bundle per OS, built in GitHub Actions on
  `macos-latest`, `windows-latest`, `ubuntu-22.04` when a `v*` tag is pushed.
- Artifacts: `Chatport-<v>.dmg`, `Chatport-<v>-Setup.exe` (Inno Setup),
  `Chatport-<v>.AppImage`.
- No code signing yet. README documents Gatekeeper "Open Anyway", SmartScreen
  "Run anyway" and `chmod +x` for the AppImage.

## README and assets

README written from scratch: hero screenshot, one-paragraph pitch, what moves
and what does not, requirements per OS, install per OS, the eight steps,
troubleshooting, privacy statement, credits (alicin, dudantas, pymobiledevice3),
license. Screenshots generated from the real app in light and dark.
App icon designed as SVG, rendered to all sizes by `packaging/make_icons.py`.

## Testing

- Unit: errors mapping, state persistence, adb discovery, OS checks (mocked).
- Jobs: run every job against `tests/fake_engine.py` with scripted success,
  cancel and each error code; assert exactly one terminal event per job.
- UI: pytest-qt drives all eight steps with the fake engine, in both languages
  and both themes; asserts Continue gating and resume-after-restart.
- Manual: one real migration with the author's phones before v1.0.0.

## Out of scope for v1

Code signing and notarization, WhatsApp Business, iCloud backups, moving
iPhone to Android, call history, reactions, polls, quoted replies.
