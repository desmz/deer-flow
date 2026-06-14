import threading
import weakref

from deerflow.sandbox.sandbox import Sandbox

# Use WeakValueDictionary to prevent memory leak in long-running processes.
# Locks are automatically removed when no longer referenced by any thread.
_LockKey = tuple[str, str]
_FILE_OPERATION_LOCKS: weakref.WeakValueDictionary[_LockKey, threading.Lock] = weakref.WeakValueDictionary()
# [DL-NOTE] Guard is required because WeakValueDictionary is not thread-safe for check-and-create;
# without it two threads could both see None and produce duplicate Lock instances for the same path.
_FILE_OPERATION_LOCKS_GUARD = threading.Lock()


# [DL-NOTE] Key is (sandbox_id, path) not just path: two sandboxes at the same virtual path
# (e.g. /mnt/user-data/workspace/out.txt) map to different physical files and must not contend.
def get_file_operation_lock_key(sandbox: Sandbox, path: str) -> tuple[str, str]:
    sandbox_id = getattr(sandbox, "id", None)
    if not sandbox_id:
        sandbox_id = f"instance:{id(sandbox)}"
    return sandbox_id, path


def get_file_operation_lock(sandbox: Sandbox, path: str) -> threading.Lock:
    lock_key = get_file_operation_lock_key(sandbox, path)
    with _FILE_OPERATION_LOCKS_GUARD:
        lock = _FILE_OPERATION_LOCKS.get(lock_key)
        if lock is None:
            lock = threading.Lock()
            _FILE_OPERATION_LOCKS[lock_key] = lock
        return lock
