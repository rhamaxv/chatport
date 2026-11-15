# Chatport on Linux

## Requirements

- A 64-bit distribution with glibc 2.35 or newer (Ubuntu 22.04, Fedora 38, Debian 12 or later).
- **usbmuxd**, the daemon that lets a computer talk to an iPhone over USB.

  | Distribution | Command |
  |---|---|
  | Debian, Ubuntu, Mint | `sudo apt install usbmuxd libimobiledevice-utils` |
  | Fedora | `sudo dnf install usbmuxd libimobiledevice-utils` |
  | Arch, Manjaro | `sudo pacman -S usbmuxd libimobiledevice` |

- A USB cable for each phone that carries data, not only charge.
- Optional: `ffmpeg`, for video thumbnails in the transferred chats.

## Install

1. Download `Chatport-<version>-x86_64.AppImage` from the Releases page.
2. Make it executable: `chmod +x Chatport-*.AppImage`.
3. Run it. If your distribution lacks FUSE 2, install `libfuse2` (Debian/Ubuntu) or run with `--appimage-extract-and-run`.

## adb

Chatport downloads Google's official Android platform-tools into its own folder the first time it needs them. If `adb` is already on your PATH, it uses that instead. On some distributions you also need udev rules for your phone; installing the `android-sdk-platform-tools-common` (Debian/Ubuntu) or `android-udev` (Arch) package provides them.

## Where Chatport keeps its files

`$XDG_DATA_HOME/chatport`, usually `~/.local/share/chatport`. The `work` folder inside holds the decrypted chats, media and iPhone backups while a transfer is in progress. The last screen lets you delete them.

## Troubleshooting

- **"usbmuxd is missing"**: install it with the command for your distribution above, then unplug and replug the iPhone.
- **The iPhone is not found although usbmuxd is installed**: run `idevice_id -l`. If it prints nothing, try `sudo systemctl restart usbmuxd`, then unlock the iPhone and tap Trust.
- **The Android phone shows as unauthorized**: unlock it and accept the "Allow USB debugging" prompt.
