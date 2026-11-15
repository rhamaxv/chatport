"""Every failure the UI can explain. Values are also the i18n key suffix: error.<value>.title / .body / .action"""
from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    # adb / Android
    NO_ADB = "no_adb"
    NO_ANDROID = "no_android"
    ANDROID_UNAUTHORIZED = "android_unauthorized"
    ANDROID_OFFLINE = "android_offline"
    SEVERAL_ANDROID = "several_android"
    NO_BACKUP_ON_ANDROID = "no_backup_on_android"
    OLD_BACKUP_FORMAT = "old_backup_format"
    ANDROID_WHATSAPP_OLD = "android_whatsapp_old"
    ANDROID_COPY_FAILED = "android_copy_failed"
    ANDROID_BACKUP_DAMAGED = "android_backup_damaged"
    # key
    KEY_FORMAT = "key_format"
    KEY_WRONG = "key_wrong"
    KEY_MISSING = "key_missing"
    # computer
    NO_SPACE = "no_space"
    ADB_DOWNLOAD_FAILED = "adb_download_failed"
    USBMUXD_MISSING = "usbmuxd_missing"          # Linux
    APPLE_SERVICE_MISSING = "apple_service_missing"  # Windows
    # iPhone
    NO_IPHONE = "no_iphone"
    IPHONE_UNTRUSTED = "iphone_untrusted"
    IPHONE_DISCONNECTED = "iphone_disconnected"
    IPHONE_ERROR = "iphone_error"
    IPHONE_BACKUP_PROBLEM = "iphone_backup_problem"
    PASSWORD_NEEDED = "password_needed"
    PASSWORD_WRONG = "password_wrong"
    FIND_MY_ON = "find_my_on"
    WHATSAPP_MISSING_ON_IPHONE = "whatsapp_missing_on_iphone"
    # build / restore
    BUILD_FAILED = "build_failed"
    NOTHING_TO_RESTORE = "nothing_to_restore"
    EARLIER_STEP_MISSING = "earlier_step_missing"
    WORKSPACE_IN_USE = "workspace_in_use"
    # generic
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


# Which action button each error offers. "retry" re-runs the job, "back" returns to the step named
# in ACTION_TARGET, "guide" opens the OS guide dialog, "log" copies the log, "none" just dismisses.
ACTION: dict[ErrorCode, str] = {
    ErrorCode.NO_ADB: "retry",
    ErrorCode.NO_ANDROID: "retry",
    ErrorCode.ANDROID_UNAUTHORIZED: "retry",
    ErrorCode.ANDROID_OFFLINE: "retry",
    ErrorCode.SEVERAL_ANDROID: "retry",
    ErrorCode.NO_BACKUP_ON_ANDROID: "retry",
    ErrorCode.OLD_BACKUP_FORMAT: "retry",
    ErrorCode.ANDROID_WHATSAPP_OLD: "retry",
    ErrorCode.ANDROID_COPY_FAILED: "retry",
    ErrorCode.ANDROID_BACKUP_DAMAGED: "back",
    ErrorCode.KEY_FORMAT: "none",
    ErrorCode.KEY_WRONG: "none",
    ErrorCode.KEY_MISSING: "back",
    ErrorCode.NO_SPACE: "retry",
    ErrorCode.ADB_DOWNLOAD_FAILED: "retry",
    ErrorCode.USBMUXD_MISSING: "guide",
    ErrorCode.APPLE_SERVICE_MISSING: "guide",
    ErrorCode.NO_IPHONE: "retry",
    ErrorCode.IPHONE_UNTRUSTED: "retry",
    ErrorCode.IPHONE_DISCONNECTED: "retry",
    ErrorCode.IPHONE_ERROR: "retry",
    ErrorCode.IPHONE_BACKUP_PROBLEM: "retry",
    ErrorCode.PASSWORD_NEEDED: "none",
    ErrorCode.PASSWORD_WRONG: "none",
    ErrorCode.FIND_MY_ON: "retry",
    ErrorCode.WHATSAPP_MISSING_ON_IPHONE: "retry",
    ErrorCode.BUILD_FAILED: "log",
    ErrorCode.NOTHING_TO_RESTORE: "back",
    ErrorCode.EARLIER_STEP_MISSING: "back",
    ErrorCode.WORKSPACE_IN_USE: "none",
    ErrorCode.CANCELLED: "none",
    ErrorCode.UNKNOWN: "log",
}
ACTION_TARGET: dict[ErrorCode, str] = {
    ErrorCode.ANDROID_BACKUP_DAMAGED: "key",
    ErrorCode.KEY_MISSING: "key",
    ErrorCode.NOTHING_TO_RESTORE: "backup",
    ErrorCode.EARLIER_STEP_MISSING: "copy",
}


# ----- mapping engine exceptions to codes -------------------------------------------------------

import errno as _errno
import re as _re

_HEX64 = _re.compile(r"[0-9a-fA-F]{64}")
_DISCONNECT_NAMES = ("ConnectionTerminated", "NoDeviceConnected", "ConnectionFailed", "DeviceNotFound",
                     "MuxException", "BrokenPipe", "ConnectionReset", "ConnectionAbortedError")


def scrub(text: str) -> str:
    """Remove anything that looks like a 64-digit key."""
    return _HEX64.sub("[key]", text)


def _type_names(exc: BaseException) -> list[str]:
    return [klass.__name__ for klass in type(exc).__mro__]


def _by_message(message: str, table: list[tuple[str, ErrorCode]], default: ErrorCode) -> ErrorCode:
    for needle, code in table:
        if needle in message:
            return code
    return default


_ADB = [("no Android phone found", ErrorCode.NO_ANDROID),
        ("accept the USB debugging prompt", ErrorCode.ANDROID_UNAUTHORIZED),
        ("adb not found", ErrorCode.NO_ADB),
        ("older backup format", ErrorCode.OLD_BACKUP_FORMAT),
        ("no WhatsApp backup", ErrorCode.NO_BACKUP_ON_ANDROID),
        ("more than one Android", ErrorCode.SEVERAL_ANDROID)]
_CRYPT = [("does not open", ErrorCode.KEY_WRONG), ("64-digit", ErrorCode.KEY_FORMAT)]
_DEVICE = [("trust", ErrorCode.IPHONE_UNTRUSTED), ("no iPhone", ErrorCode.NO_IPHONE)]
_FAILURE = [("failed its checks", ErrorCode.BUILD_FAILED), ("refusing to restore", ErrorCode.BUILD_FAILED),
            ("already", ErrorCode.WORKSPACE_IN_USE)]
_IOS_BACKUP = [("password is wrong", ErrorCode.PASSWORD_WRONG), ("password is needed", ErrorCode.PASSWORD_NEEDED)]


def _friendly(exc: BaseException) -> tuple[ErrorCode, dict]:
    """Turn any exception the engine can raise into an ErrorCode plus data the UI may show."""
    from .keygrid import KeyProblem

    if isinstance(exc, KeyProblem):
        return ErrorCode(exc.code), {}
    names = _type_names(exc)
    if "AdbDownloadError" in names:
        return ErrorCode.ADB_DOWNLOAD_FAILED, {"detail": scrub(str(exc))[:300]}
    mapped = _engine_code(exc)
    if mapped is not None:
        return mapped
    if any(any(part in name for part in _DISCONNECT_NAMES) for name in names):
        return ErrorCode.IPHONE_DISCONNECTED, {}
    if isinstance(exc, OSError) and exc.errno == _errno.ENOSPC:
        return ErrorCode.NO_SPACE, {}
    return ErrorCode.UNKNOWN, {"detail": scrub(f"{type(exc).__name__}: {exc}")[:300]}


def _engine_code(exc: BaseException) -> tuple[ErrorCode, dict] | None:
    from wamove import api
    from wamove.android import adb, crypt15, msgstore
    from wamove.cli import Failure
    from wamove.ios import backup as ios_backup
    from wamove.ios import chatstorage, device

    message = str(exc)
    if isinstance(exc, api.NotEnoughSpace):
        return ErrorCode.NO_SPACE, {"needed": exc.needed, "free": exc.free}
    plain = {api.Cancelled: ErrorCode.CANCELLED, api.NothingToRestore: ErrorCode.NOTHING_TO_RESTORE,
             api.FindMyOn: ErrorCode.FIND_MY_ON, api.PasswordNeeded: ErrorCode.PASSWORD_NEEDED,
             api.WhatsAppMissing: ErrorCode.WHATSAPP_MISSING_ON_IPHONE,
             msgstore.MsgstoreError: ErrorCode.ANDROID_WHATSAPP_OLD,
             chatstorage.ChatStorageError: ErrorCode.BUILD_FAILED}
    for klass, code in plain.items():
        if isinstance(exc, klass):
            return code, {}
    by_message = [(adb.AdbError, _ADB, ErrorCode.ANDROID_COPY_FAILED),
                  (crypt15.Crypt15Error, _CRYPT, ErrorCode.ANDROID_BACKUP_DAMAGED),
                  (device.DeviceError, _DEVICE, ErrorCode.IPHONE_ERROR),
                  (Failure, _FAILURE, ErrorCode.EARLIER_STEP_MISSING),
                  (ios_backup.BackupError, _IOS_BACKUP, ErrorCode.IPHONE_BACKUP_PROBLEM)]
    for klass, table, default in by_message:
        if isinstance(exc, klass):
            return _by_message(message, table, default), {}
    return None


def friendly(exc: BaseException) -> tuple[ErrorCode, dict]:
    """Map an exception to an error code, keeping the engine's own explanation for build failures."""
    code, data = _friendly(exc)
    if code is ErrorCode.BUILD_FAILED and not data.get("detail"):
        data["detail"] = scrub(str(exc))[:600]
    return code, data
