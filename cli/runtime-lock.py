"""Run one runtime preparation while holding a native, process-owned file lock."""

import errno
import os
from pathlib import Path
import subprocess
import sys
import time


def run_locked(lock_path, command):
    lock_path = Path(lock_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Keep this file in place: unlinking it could let waiters lock different
    # inodes. The OS releases the lock if its process exits unexpectedly.
    with lock_path.open("a+b") as lock:
        if os.name == "nt":
            import msvcrt

            if lock_path.stat().st_size == 0:
                lock.write(b"\0")
                lock.flush()

            def acquire():
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)

            def release():
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            def acquire():
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release():
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

        deadline = time.monotonic() + 300
        while True:
            try:
                acquire()
                break
            except OSError as error:
                if error.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if time.monotonic() >= deadline:
                    raise RuntimeError(
                        "Another process is preparing the Python runtime. "
                        "Wait for it to finish, then retry."
                    ) from error
                time.sleep(0.1)
        try:
            return subprocess.run(command, check=False).returncode
        finally:
            release()


if __name__ == "__main__":
    try:
        sys.exit(run_locked(sys.argv[1], sys.argv[2:]))
    except (OSError, RuntimeError) as error:
        print(f"AI-Shifu runtime: {error}", file=sys.stderr)
        sys.exit(1)
