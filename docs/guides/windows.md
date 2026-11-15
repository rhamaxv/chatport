# Chatport on Windows

## Requirements

- Windows 10 or 11, 64-bit.
- **Apple Mobile Device Support.** Chatport talks to the iPhone through Apple's USB driver. The easiest way to get it is to install iTunes from the Microsoft Store, open it once, and plug in the iPhone so Windows finishes installing the driver. You can close iTunes afterwards; only its background service is needed.
- A USB cable for each phone that carries data, not only charge.

## Install

1. Download `Chatport-<version>-Setup.exe` from the Releases page.
2. Run it. Windows SmartScreen shows "Windows protected your PC" because the installer is not signed yet. Click **More info**, then **Run anyway**.
3. Start Chatport from the Start menu.

## adb

Chatport downloads Google's official Android platform-tools into its own folder the first time it needs them. If you already have `adb` on your PATH, it uses that instead.

## Where Chatport keeps its files

`%LOCALAPPDATA%\Chatport`. The `work` folder inside holds the decrypted chats, media and iPhone backups while a transfer is in progress. The last screen lets you delete them.

## Troubleshooting

- **"Apple Mobile Device Service is not running"**: open Services (Win+R, `services.msc`), find *Apple Mobile Device Service*, right-click, Start. If it is not listed, reinstall iTunes from the Microsoft Store.
- **The iPhone shows as untrusted**: unlock the iPhone, tap **Trust** on the prompt, and enter its passcode.
- **The Android phone shows as unauthorized**: unlock it and accept the "Allow USB debugging" prompt. Tick "Always allow from this computer".
