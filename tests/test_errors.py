import errno

import pytest
from wamove import api
from wamove.android import adb, crypt15, msgstore
from wamove.cli import Failure
from wamove.ios import backup as ios_backup
from wamove.ios import chatstorage, device

from chatport.core.errors import ErrorCode, friendly, scrub
from chatport.core.keygrid import KeyProblem

KEY = "ab" * 32


class ConnectionTerminated(Exception):
    pass


class MuxException(Exception):
    pass


class AdbDownloadError(Exception):
    pass


CASES = [
    (api.Cancelled(), ErrorCode.CANCELLED),
    (KeyProblem("key_format"), ErrorCode.KEY_FORMAT),
    (KeyProblem("key_wrong"), ErrorCode.KEY_WRONG),
    (KeyProblem("key_missing"), ErrorCode.KEY_MISSING),
    (adb.AdbError("no Android phone found: turn on USB debugging"), ErrorCode.NO_ANDROID),
    (adb.AdbError("the Android phone is 'unauthorized': unlock it and accept the USB debugging prompt"),
     ErrorCode.ANDROID_UNAUTHORIZED),
    (adb.AdbError("adb not found; install Android Platform Tools"), ErrorCode.NO_ADB),
    (adb.AdbError("the phone only has an older backup format: ..."), ErrorCode.OLD_BACKUP_FORMAT),
    (adb.AdbError("no WhatsApp backup on the phone"), ErrorCode.NO_BACKUP_ON_ANDROID),
    (adb.AdbError("more than one Android device is connected"), ErrorCode.SEVERAL_ANDROID),
    (adb.AdbError("adb pull /sdcard/x failed"), ErrorCode.ANDROID_COPY_FAILED),
    (crypt15.Crypt15Error("the key does not open this backup"), ErrorCode.KEY_WRONG),
    (crypt15.Crypt15Error("the key must be the 64-digit end-to-end backup key"), ErrorCode.KEY_FORMAT),
    (crypt15.Crypt15Error("truncated varint"), ErrorCode.ANDROID_BACKUP_DAMAGED),
    (msgstore.MsgstoreError("no messages table"), ErrorCode.ANDROID_WHATSAPP_OLD),
    (device.DeviceError("the iPhone does not trust this computer yet"), ErrorCode.IPHONE_UNTRUSTED),
    (device.DeviceError("no iPhone found: plug it in"), ErrorCode.NO_IPHONE),
    (device.DeviceError("could not reach the iPhone's backup service"), ErrorCode.IPHONE_ERROR),
    (api.NothingToRestore(), ErrorCode.NOTHING_TO_RESTORE),
    (api.FindMyOn(), ErrorCode.FIND_MY_ON),
    (api.PasswordNeeded(), ErrorCode.PASSWORD_NEEDED),
    (api.WhatsAppMissing(), ErrorCode.WHATSAPP_MISSING_ON_IPHONE),
    (Failure("this workspace already contains Android data"), ErrorCode.WORKSPACE_IN_USE),
    (Failure("there is no iPhone backup yet; run `wamove backup` first"), ErrorCode.EARLIER_STEP_MISSING),
    (Failure("the converted database failed its checks:\n  x"), ErrorCode.BUILD_FAILED),
    (Failure("this build is incomplete or its manifest changed; refusing to restore"), ErrorCode.BUILD_FAILED),
    (ios_backup.BackupError("the backup password is wrong"), ErrorCode.PASSWORD_WRONG),
    (ios_backup.BackupError("this iPhone backup is encrypted, so its backup password is needed"),
     ErrorCode.PASSWORD_NEEDED),
    (ios_backup.BackupError("/x is not an iPhone backup"), ErrorCode.IPHONE_BACKUP_PROBLEM),
    (chatstorage.ChatStorageError("bad schema"), ErrorCode.BUILD_FAILED),
    (ConnectionTerminated(), ErrorCode.IPHONE_DISCONNECTED),
    (MuxException("usbmuxd went away"), ErrorCode.IPHONE_DISCONNECTED),
    (BrokenPipeError(), ErrorCode.IPHONE_DISCONNECTED),
    (ConnectionResetError(), ErrorCode.IPHONE_DISCONNECTED),
    (ConnectionAbortedError(), ErrorCode.IPHONE_DISCONNECTED),
    (OSError(errno.ENOSPC, "No space left on device"), ErrorCode.NO_SPACE),
    (AdbDownloadError("404"), ErrorCode.ADB_DOWNLOAD_FAILED),
    (ValueError("odd"), ErrorCode.UNKNOWN),
]


@pytest.mark.parametrize("exc,code", CASES, ids=[type(e).__name__ + ":" + c.value for e, c in CASES])
def test_mapping(exc, code):
    got, data = friendly(exc)
    assert got is code
    assert isinstance(data, dict)


def test_no_space_carries_sizes():
    code, data = friendly(api.NotEnoughSpace(10, 3))
    assert code is ErrorCode.NO_SPACE
    assert data == {"needed": 10, "free": 3}


def test_unknown_detail_is_typed_and_scrubbed():
    code, data = friendly(RuntimeError(f"boom with key {KEY} inside"))
    assert code is ErrorCode.UNKNOWN
    assert data["detail"].startswith("RuntimeError: boom")
    assert KEY not in data["detail"]
    assert "[key]" in data["detail"]


def test_unknown_detail_is_capped():
    _, data = friendly(RuntimeError("x" * 1000))
    assert len(data["detail"]) == 300


def test_scrub_only_touches_64_hex_runs():
    assert scrub("abc 1234 " + KEY.upper()) == "abc 1234 [key]"
    assert scrub("f" * 63) == "f" * 63
