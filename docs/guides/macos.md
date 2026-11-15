# Chatport on macOS

## Requirements

- macOS 12 Monterey or newer, Apple silicon or Intel.
- A USB cable for each phone that carries data, not only charge.
- Optional: `ffmpeg` (`brew install ffmpeg`), for video thumbnails in the transferred chats.

## Install

1. Download `Chatport-<version>.dmg` from the Releases page.
2. Open it and drag Chatport to Applications.
3. Open Chatport. macOS says it cannot verify the developer because the app is not notarized yet. Click **Done**, open **System Settings > Privacy & Security**, scroll to Security and click **Open Anyway**. You only do this once.

   Or, in Terminal: `xattr -dr com.apple.quarantine /Applications/Chatport.app`

## adb

Chatport downloads Google's official Android platform-tools into its own folder the first time it needs them. If `adb` is already installed (for example with `brew install --cask android-platform-tools`), it uses that instead.

## Where Chatport keeps its files

`~/Library/Application Support/Chatport`. The `work` folder inside holds the decrypted chats, media and iPhone backups while a transfer is in progress. The last screen lets you delete them. Logs are in `~/Library/Logs/Chatport`.

## Troubleshooting

- **The iPhone shows as untrusted**: unlock it, tap **Trust** on the prompt, and enter its passcode. If no prompt appears, unplug and replug the cable.
- **The Android phone shows as unauthorized**: unlock it and accept the "Allow USB debugging" prompt.
- **Finder says "Encrypt local backup" is on**: untick it in Finder with the iPhone selected. Chatport needs an unencrypted backup unless you give it the backup password.
