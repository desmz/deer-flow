import fnmatch
import os
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# [DL-NOTE] Intentionally cross-ecosystem: covers Python (.venv, __pycache__), JS (node_modules, .next),
# Java (target), VCS (.git, .svn), IDEs (.idea, .vscode), and OS artifacts (.DS_Store).
IGNORE_PATTERNS = [
    ".git",
    ".svn",
    ".hg",
    ".bzr",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".env",
    "env",
    ".tox",
    ".nox",
    ".eggs",
    "*.egg-info",
    "site-packages",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".output",
    ".turbo",
    "target",
    "out",
    ".idea",
    ".vscode",
    "*.swp",
    "*.swo",
    "*~",
    ".project",
    ".classpath",
    ".settings",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    "*.lnk",
    "*.log",
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.cache",
    ".cache",
    "logs",
    ".coverage",
    "coverage",
    ".nyc_output",
    "htmlcov",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
]

DEFAULT_MAX_FILE_SIZE_BYTES = 1_000_000
DEFAULT_LINE_SUMMARY_LENGTH = 200


@dataclass(frozen=True)
class GrepMatch:
    path: str
    line_number: int
    line: str


def should_ignore_name(name: str) -> bool:
    for pattern in IGNORE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


# [DL-NOTE] Checks every path segment, not just the filename — `foo/node_modules/bar.js` is rejected
# at the `node_modules` segment. Used by AioSandbox to filter remote file listings from the backend.
def should_ignore_path(path: str) -> bool:
    return any(should_ignore_name(segment) for segment in path.replace("\\", "/").split("/") if segment)


# [DL-INSIGHT] PurePosixPath.match() anchors from the right, so "*.py" matches "foo/bar.py".
# The `**/` branch is a fallback: strips the prefix so "**/*.py" also matches top-level files.
def path_matches(pattern: str, rel_path: str) -> bool:
    path = PurePosixPath(rel_path)
    if path.match(pattern):
        return True
    if pattern.startswith("**/"):
        return path.match(pattern[3:])
    return False


def truncate_line(line: str, max_chars: int = DEFAULT_LINE_SUMMARY_LENGTH) -> str:
    line = line.rstrip("\n\r")
    if len(line) <= max_chars:
        return line
    return line[: max_chars - 3] + "..."


def is_binary_file(path: Path, sample_size: int = 8192) -> bool:
    try:
        with path.open("rb") as handle:
            return b"\0" in handle.read(sample_size)
    except OSError:
        return True


def find_glob_matches(root: Path, pattern: str, *, include_dirs: bool = False, max_results: int = 200) -> tuple[list[str], bool]:
    matches: list[str] = []
    truncated = False
    root = root.resolve()

    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise NotADirectoryError(root)

    for current_root, dirs, files in os.walk(root):
        # [DL-INSIGHT] In-place slice mutation `dirs[:] = ...` is required; `dirs = [...]` would not
        # suppress os.walk recursion into ignored directories like node_modules.
        dirs[:] = [name for name in dirs if not should_ignore_name(name)]
        # root is already resolved; os.walk builds current_root by joining under root,
        # so relative_to() works without an extra stat()/resolve() per directory.
        rel_dir = Path(current_root).relative_to(root)

        if include_dirs:
            for name in dirs:
                rel_path = (rel_dir / name).as_posix()
                if path_matches(pattern, rel_path):
                    matches.append(str(Path(current_root) / name))
                    if len(matches) >= max_results:
                        truncated = True
                        return matches, truncated

        for name in files:
            if should_ignore_name(name):
                continue
            rel_path = (rel_dir / name).as_posix()
            if path_matches(pattern, rel_path):
                matches.append(str(Path(current_root) / name))
                if len(matches) >= max_results:
                    truncated = True
                    return matches, truncated

    return matches, truncated


def find_grep_matches(
    root: Path,
    pattern: str,
    *,
    glob_pattern: str | None = None,
    literal: bool = False,
    case_sensitive: bool = False,
    max_results: int = 100,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    line_summary_length: int = DEFAULT_LINE_SUMMARY_LENGTH,
) -> tuple[list[GrepMatch], bool]:
    matches: list[GrepMatch] = []
    truncated = False
    root = root.resolve()

    if not root.exists():
        raise FileNotFoundError(root)
    if not root.is_dir():
        raise NotADirectoryError(root)

    regex_source = re.escape(pattern) if literal else pattern
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(regex_source, flags)

    # [DL-NOTE] Minified JS/CSS files can be a single line of hundreds of KB; a pathological
    # regex on such a line causes catastrophic backtracking. 10× the summary length is the heuristic.
    # Skip lines longer than this to prevent ReDoS on minified / no-newline files.
    _max_line_chars = line_summary_length * 10

    for current_root, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if not should_ignore_name(name)]
        rel_dir = Path(current_root).relative_to(root)

        for name in files:
            if should_ignore_name(name):
                continue

            candidate_path = Path(current_root) / name
            rel_path = (rel_dir / name).as_posix()

            if glob_pattern is not None and not path_matches(glob_pattern, rel_path):
                continue

            try:
                # [DL-WARN] Two-layer path-traversal guard: skip symlinks entirely, then verify
                # the resolved path stays within root (belt-and-suspenders against `../` tricks).
                if candidate_path.is_symlink():
                    continue
                file_path = candidate_path.resolve()
                if not file_path.is_relative_to(root):
                    continue
                if file_path.stat().st_size > max_file_size or is_binary_file(file_path):
                    continue
                with file_path.open(encoding="utf-8", errors="replace") as handle:
                    for line_number, line in enumerate(handle, start=1):
                        if len(line) > _max_line_chars:
                            continue
                        if regex.search(line):
                            matches.append(
                                GrepMatch(
                                    path=str(file_path),
                                    line_number=line_number,
                                    line=truncate_line(line, line_summary_length),
                                )
                            )
                            if len(matches) >= max_results:
                                truncated = True
                                return matches, truncated
            except OSError:
                continue

    return matches, truncated
