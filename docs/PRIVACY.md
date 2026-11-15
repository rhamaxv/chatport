# Privacy

Chatport moves your WhatsApp chats from an Android phone to an iPhone. Those chats are the most private data most people own, so this page says exactly what the app does with them. It is written to be checked against the source code, and the rules below are also the rules in `CLAUDE.md` and `CONTRIBUTING.md` that every change has to follow.

## The short version

- Nothing is uploaded anywhere. Chatport has no server, no account, no telemetry and no crash reporting.
- The only network call is downloading Google's Android platform-tools, and only when `adb` is not already installed.
- The 64-digit backup key lives in memory only.
- Everything Chatport produces sits in one folder on your computer that only your user can read, and the last screen can delete it.
- Logs never contain the key, phone numbers or message text.

## Network

Chatport makes exactly one kind of network request: on the Connect screen, when `adb` is not found on this computer and you click **Install adb**, it downloads `platform-tools-latest-<os>.zip` from `https://dl.google.com/android/repository/`. That is Google's official download, fetched directly, with no intermediary. If `adb` is already on your PATH, this never happens.

Nothing else talks to the network. Not the engine, not the update of the Connect cards, not the error screens. There is no update check. You learn about new versions from the GitHub releases page.

## The backup key

The 64-digit key that WhatsApp shows on the Android phone is what decrypts your chats. Chatport treats it like this:

- It is held in memory for the duration of the session and passed to the engine in-process.
- It is never written to disk, not in the work folder, not in `state.json`, not in settings.
- It is never written to the log. The error reporter runs every message through a filter that replaces anything shaped like a 64-digit hexadecimal string with `[key]` before it is logged or shown.
- If you close Chatport and reopen it, the key is gone and the app asks for it again.

If the iPhone encrypts its backups, Chatport asks for that backup password too. It is handled the same way: memory only, never on disk, never in the log.

## Where your data lives

Chatport keeps everything under one data folder, created with permissions that allow only your user account to read it:

| System | Data folder |
|---|---|
| macOS | `~/Library/Application Support/Chatport` |
| Windows | `%LOCALAPPDATA%\Chatport` |
| Linux | `$XDG_DATA_HOME/chatport`, usually `~/.local/share/chatport` |

Setting the environment variable `CHATPORT_DATA_DIR` moves this folder somewhere else, for example to an external drive.

Inside that folder:

- `work/` holds the data of the transfer in progress: the copied Android backup and media, the decrypted database, the full iPhone backup, the WhatsApp-only copy before the merge, the merged copy, the coverage report and `state.json` (which steps are done). This is where your chats are, in readable form, while Chatport works.
- `logs/chatport.log` is the application log, rotated at 2 MB with three older files kept.
- `platform-tools/` is the downloaded `adb`, if Chatport downloaded it.

## Deleting your data

On the **Done** screen, **Delete private copies** removes the Android chats, media and the WhatsApp copies from `work/`. A checkbox lets you also delete the full iPhone backup. Chatport keeps that backup by default because it is your way back; delete it once you are sure the iPhone is fine.

If you prefer to do it by hand, deleting the whole data folder above removes everything, including the log and the downloaded `adb`.

If you stop part way through and never come back, the files in `work/` stay there. They are not sent anywhere and they are not cleaned up automatically. Delete the folder yourself if you do not finish.

## Logs

The log exists so a problem can be diagnosed from a bug report. It contains:

- Chatport's version and the operating system.
- Which step started and finished, with timing and percentages.
- Error types and the titles shown to you.
- Counts, such as how many messages were added or how many media files were missing.

It does not contain the backup key, the iPhone backup password, phone numbers, contact names, message text or file names of your media. The **Copy log** button on every error card copies this log to the clipboard, and it is safe to paste into a public issue. Do not attach the contents of `work/` to an issue.

## What happens on the phones

- **Android phone**: Chatport only reads. It copies the WhatsApp backup file and the media folders over USB with `adb`. It does not change, delete or write anything on the Android phone, which is why you can keep using it as a fallback.
- **iPhone**: Chatport makes a full backup (read), then restores a backup that contains only WhatsApp's data (write). No other app's data is written. The restore uses the same mechanism as Finder or iTunes, through the open source pymobiledevice3 library.

## Third parties

Chatport's engine is [wamove](https://github.com/rhamaxv/wamove), which runs inside the same process and follows the same rules. It depends on [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) for the iPhone and on Google's `adb` for Android. None of these send your data anywhere. Chatport does not use any analytics, advertising or crash-reporting SDK.

## Questions

If anything on this page does not match what the code does, that is a bug. Open an issue at <https://github.com/rhamaxv/chatport/issues>.
