# Frequently asked questions

Questions people ask before, during and after a move. For installation problems on one system, see the guide for [macOS](guides/macos.md), [Windows](guides/windows.md) or [Linux](guides/linux.md).

## Is this safe? Can I lose anything on the iPhone?

Chatport does three things to the iPhone, in this order: it reads a full backup, it keeps that backup untouched on your computer, and it restores a backup that contains only WhatsApp's data. Photos, other apps, settings and accounts are not in the restored backup, so they are not written. The iPhone restarts once, the home screen layout can reset, and some apps may download again from the App Store, which is normal after any restore.

The things that can go wrong are inside WhatsApp: a chat that did not merge the way you expected, or media that was missing on the Android phone. The Build step lists both before you restore, and Undo puts WhatsApp back afterwards. The Android phone is only read, never changed, so keep it as it is until you are happy.

## Can I go back?

Yes. On the Done screen, **Undo** restores the WhatsApp-only copy that Chatport saved before merging anything. The iPhone restarts once more and WhatsApp is exactly as it was before Chatport. The full backup from step 6 also stays on your computer until you delete it.

If you have already closed Chatport, open it again. It resumes on the Done screen as long as the files in the work folder still exist.

## Some group chats are missing or empty

First look at the Build report (step 7). Groups that were never in the Android backup cannot come across, so if a group is missing there, make a fresh backup on the Android phone (WhatsApp > Settings > Chats > Chat backup > Back up) and start again from the Connect screen. Groups you left on Android come across with their history but no members.

If a group is listed as created or merged in the report but shows nothing on the iPhone, open it once with Airplane mode off and wait a moment. WhatsApp fills in members and group names from the server when the chat is first opened.

If it is still empty, that is a bug in the engine. Use Copy log on the error card, or send the log from the data folder, and open an issue. Do not attach your chats.

## The WhatsApp icon (or another app icon) looks faded after the restore

After a restore, iOS checks every app against the App Store and re-downloads any it decides it needs to. A faded or dimmed icon with a progress ring means that download is queued or in progress. Keep the iPhone on Wi-Fi and unlocked, and tap the icon to prioritise it. Your WhatsApp data is already on the phone; it is only the app binary that is downloading.

## A disappearing-message timer shows on a chat

Disappearing-message settings are one of the things that do not come across cleanly. A chat may show a timer notice it did not have, or lose the one it had. Open the chat, tap the name at the top, choose **Disappearing messages** and set it to what you want. It is a per-chat setting and takes a second each.

## Find My is on but the switch is greyed out

Chatport needs Find My iPhone off because iOS refuses to restore a backup while Activation Lock is active. If the switch under Settings > your name > Find My > Find My iPhone is grey:

- Check Settings > Screen Time > Content & Privacy Restrictions. If **Account Changes** or **Location Services** is set to Don't Allow, set it to Allow, then try again.
- If the iPhone is managed by a school or employer, a profile may lock Find My. Ask the administrator.
- Turning it off asks for your Apple ID password. That is normal.

Turn Find My back on after the move is done.

## Finder or iTunes says backup encryption is on and I do not know the password

You have two options. Either enter the password when Chatport asks for it on the Back up iPhone screen (it stays in memory only), or remove the encryption. Apple's way to remove a forgotten backup password is Settings > General > Transfer or Reset iPhone > Reset > **Reset All Settings**. That clears settings like wallpaper and Wi-Fi passwords but keeps your data and apps. After that, untick Encrypt local backup in Finder or iTunes with the iPhone selected.

## The Android phone shows as "unauthorized"

The Android phone has not yet allowed this computer to use USB debugging. Unlock the phone and look for the "Allow USB debugging?" prompt. Tick **Always allow from this computer** and tap Allow. If no prompt appears, unplug the cable, plug it back in, and on the phone open Developer options and tap **Revoke USB debugging authorizations**, then try again.

If the phone does not appear at all, make sure Developer options and USB debugging are on, and that the cable carries data. Many charging cables do not.

## Linux: usbmuxd is missing, or the iPhone is not found

`usbmuxd` is the daemon Linux needs to talk to iPhones. Install it with your package manager:

| Distribution | Command |
|---|---|
| Debian, Ubuntu, Mint | `sudo apt install usbmuxd libimobiledevice-utils` |
| Fedora | `sudo dnf install usbmuxd libimobiledevice-utils` |
| Arch, Manjaro | `sudo pacman -S usbmuxd libimobiledevice` |

Then unplug and replug the iPhone. If it is installed and the iPhone still does not appear, run `idevice_id -l`. If it prints nothing, try `sudo systemctl restart usbmuxd`, unlock the iPhone and tap Trust.

## Windows: "Apple Mobile Device Service is missing" or not running

Chatport talks to the iPhone through Apple's driver, which comes with iTunes from the Microsoft Store. Install iTunes, open it once, and plug in the iPhone so Windows finishes installing the driver. You can close iTunes afterwards.

If the service is installed but not running, press Win+R, type `services.msc`, find **Apple Mobile Device Service**, right-click it and choose Start. If it is not listed at all, reinstall iTunes from the Microsoft Store.

## Something else

Open an issue at <https://github.com/rhamaxv/chatport/issues> with your operating system, the Chatport version, the step where it stopped and the error title. Attach the log from the Copy log button. It never contains your key or phone numbers.


## Where are my favourite stickers?

Chatport copies WhatsApp's own backup of your favourites from the Android phone and adds them to
the sticker tray on the iPhone, so they appear under Favourites after the restore. Sticker packs you
installed from the store or from third-party apps are not copied: install them again on the iPhone.
If the Build report says some favourites could not be read, their files were no longer on the Android
phone.
