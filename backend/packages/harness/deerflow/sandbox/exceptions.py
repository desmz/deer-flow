"""Sandbox-related exceptions with structured error information."""

# [DL-INSIGHT] Two-level hierarchy: SandboxError → command/file/runtime/notfound; SandboxFileError → permission/notfound.
# Mirrors Python's built-in OSError tree but scoped to sandbox so callers can distinguish OS failures from sandbox-level ones.
class SandboxError(Exception):
    """Base exception for all sandbox-related errors."""

    # [DL-NOTE] details dict accumulates structured context per subclass; __str__ flattens it to key=value for log readability.
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            detail_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({detail_str})"
        return self.message


class SandboxNotFoundError(SandboxError):
    """Raised when a sandbox cannot be found or is not available."""

    def __init__(self, message: str = "Sandbox not found", sandbox_id: str | None = None):
        details = {"sandbox_id": sandbox_id} if sandbox_id else None
        super().__init__(message, details)
        self.sandbox_id = sandbox_id


# [DL-NOTE] No custom __init__: raised when the sandbox *infrastructure* is misconfigured, not when a specific instance is missing.
# Use SandboxNotFoundError when a sandbox_id lookup fails; SandboxRuntimeError when the system itself won't start.
class SandboxRuntimeError(SandboxError):
    """Raised when sandbox runtime is not available or misconfigured."""

    pass


class SandboxCommandError(SandboxError):
    """Raised when a command execution fails in the sandbox."""

    # [DL-NOTE] command is truncated to 100 chars in details to prevent log flooding; full command is preserved in self.command.
    def __init__(self, message: str, command: str | None = None, exit_code: int | None = None):
        details = {}
        if command:
            details["command"] = command[:100] + "..." if len(command) > 100 else command
        if exit_code is not None:
            details["exit_code"] = exit_code
        super().__init__(message, details)
        self.command = command
        self.exit_code = exit_code


class SandboxFileError(SandboxError):
    """Raised when a file operation fails in the sandbox."""

    def __init__(self, message: str, path: str | None = None, operation: str | None = None):
        details = {}
        if path:
            details["path"] = path
        if operation:
            details["operation"] = operation
        super().__init__(message, details)
        self.path = path
        self.operation = operation


class SandboxPermissionError(SandboxFileError):
    """Raised when a permission error occurs during file operations."""

    pass


class SandboxFileNotFoundError(SandboxFileError):
    """Raised when a file or directory is not found."""

    pass
