"""Independent ChatGPT credentials; never read another project's configuration."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import getpass
import os
from pathlib import Path

from .errors import ValidationError
from .storage import ccw_home


class _Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def credential_path(path=None):
    return Path(path).expanduser().resolve() if path else ccw_home() / "http" / "credentials.dpapi"


def _protect(data: bytes, *, decrypt=False):
    if os.name != "nt":
        raise ValidationError("DPAPI credential storage requires Windows; use CCW_CHATGPT_ACCESS_TOKEN")
    buffer = ctypes.create_string_buffer(data)
    source = _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = _Blob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    # CRYPTPROTECT_UI_FORBIDDEN; current-user protection, never LOCAL_MACHINE.
    if decrypt:
        crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
        ok = crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target))
    else:
        crypt32.CryptProtectData.argtypes = [ctypes.POINTER(_Blob), wintypes.LPCWSTR,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
        ok = crypt32.CryptProtectData(ctypes.byref(source), "CCW independent HTTP credential", None,
            None, None, 1, ctypes.byref(target))
    if not ok:
        raise ValidationError("credential protection unavailable")
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel32.LocalFree(ctypes.cast(target.data, ctypes.c_void_p))


def _validate_token(token):
    if not isinstance(token, str) or not 20 <= len(token) <= 32768 or any(c.isspace() for c in token):
        raise ValidationError("invalid ChatGPT access token")
    return token


def store_access_token(token, path=None):
    token = _validate_token(token.strip())
    encrypted = _protect(token.encode("utf-8"))
    destination = credential_path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix="credential-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encrypted)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"configured": True, "storage": "windows-current-user-dpapi"}


def load_access_token(path=None):
    token = os.environ.get("CCW_CHATGPT_ACCESS_TOKEN")
    if token:
        return _validate_token(token)
    try:
        destination = credential_path(path)
        if destination.stat().st_size > 65536:
            raise ValueError()
        return _validate_token(_protect(destination.read_bytes(), decrypt=True).decode("utf-8"))
    except Exception:
        raise ValidationError("independent ChatGPT HTTP credential unavailable; run http credentials-set") from None


def configure_credentials(path=None):
    # Only an interactive, echo-free terminal receives the credential.
    import sys
    if not sys.stdin.isatty():
        raise ValidationError("credential setup requires an interactive terminal")
    token = getpass.getpass("ChatGPT access token (hidden; never paste into chat): ")
    return store_access_token(token, path)
