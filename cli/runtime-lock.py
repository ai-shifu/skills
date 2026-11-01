"""Keep runtime preparation exclusive until its last inherited handle closes."""

import errno
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

IMPORT_CHECK = "import requests, dotenv, PIL, pillow_heif"


def prepare_runtime(directory, requirements, python, lock, run=subprocess.run):
    directory = Path(directory)
    marker = directory / ".ready"
    if marker.exists() and Path(python).exists():
        try:
            result = run(
                [python, "-c", IMPORT_CHECK], stdin=lock, check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
            )
            if result.returncode == 0:
                return 0
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                "Python runtime validation timed out. The cached installation "
                "was left unchanged; retry shifu setup."
            ) from error
        except OSError:
            pass
    if Path(sys.prefix).resolve() == directory.resolve():
        # Windows cannot remove the executable of this running helper. A
        # cached interpreter is a valid launcher only while its runtime works.
        raise RuntimeError(
            "The cached Python runtime needs repair and was left unchanged. "
            "Set AI_SHIFU_PYTHON to an external Python 3.11+ executable, "
            "then retry shifu setup."
        )
    if directory.is_symlink():
        directory.unlink()
    elif directory.exists():
        shutil.rmtree(directory)
    directory.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    print("Preparing the isolated AI-Shifu Python runtime…", file=sys.stderr)
    # Python passes the original lock handle directly to every mutator. There
    # is no intermediate Node CRT descriptor table on Windows.
    run([sys.executable, "-m", "venv", str(directory)], stdin=lock, check=True)
    run(
        [python, "-m", "pip", "install", "--disable-pip-version-check", "-r", requirements],
        stdin=lock, check=True, stdout=sys.stderr,
    )
    run([python, "-c", IMPORT_CHECK], stdin=lock, check=True)
    marker.write_text("ready\n", encoding="utf-8", newline="\n")
    marker.chmod(0o600)
    return 0


def acquire(lock_path):
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        import msvcrt

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = [
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
        ]
        create_file.restype = wintypes.HANDLE
        # Unlike Windows byte-range locks, CreateFile's sharing restrictions
        # remain in effect for inherited or duplicated handles. Passing this
        # handle as worker stdin keeps it open if this helper is terminated.
        handle = create_file(str(lock_path), 0x80000000 | 0x40000000, 0, None, 4, 0x80, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
        except BaseException:
            close_handle = kernel32.CloseHandle
            close_handle.argtypes = [wintypes.HANDLE]
            close_handle.restype = wintypes.BOOL
            close_handle(handle)
            raise
        return os.fdopen(descriptor, "r+b")

    import fcntl

    lock = lock_path.open("a+b")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        lock.close()
        raise
    return lock


def run_locked(lock_path, command):
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Keep this file in place so all waiters open the same inode/file object.
    deadline = time.monotonic() + 300
    while True:
        try:
            lock = acquire(lock_path)
            break
        except OSError as error:
            busy = getattr(error, "winerror", None) == 32 if os.name == "nt" else error.errno in (errno.EACCES, errno.EAGAIN)
            if not busy:
                raise
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Another process is preparing the Python runtime. "
                    "Wait for it to finish, then retry."
                ) from error
            time.sleep(0.1)
    with lock:
        # Runtime setup is non-interactive. Its otherwise unused stdin carries
        # the lock through the venv/pip subprocesses. Do not
        # explicitly unlock: an orphaned worker may still own a duplicate.
        if command[0] == "--prepare":
            return prepare_runtime(*command[1:], lock)
        return subprocess.run(command, check=False, stdin=lock).returncode


if __name__ == "__main__":
    try:
        sys.exit(run_locked(sys.argv[1], sys.argv[2:]))
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"AI-Shifu runtime: {error}", file=sys.stderr)
        sys.exit(1)
