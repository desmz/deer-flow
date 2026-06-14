from pathlib import Path

from deerflow.sandbox.search import should_ignore_name


def list_dir(path: str, max_depth: int = 2) -> list[str]:
    """
    List files and directories up to max_depth levels deep.

    Args:
        path: The root directory path to list.
        max_depth: Maximum depth to traverse (default: 2).
                   1 = only direct children, 2 = children + grandchildren, etc.

    Returns:
        A list of absolute paths for files and directories,
        excluding items matching IGNORE_PATTERNS.
    """
    result: list[str] = []
    root_path = Path(path).resolve()

    if not root_path.is_dir():
        return result

    # [DL-INSIGHT] Uses Path.relative_to() as the sandbox boundary check; ValueError means the resolved path escapes root_path.
    def _is_within_root(candidate: Path) -> bool:
        try:
            candidate.relative_to(root_path)
            return True
        except ValueError:
            return False

    def _traverse(current_path: Path, current_depth: int) -> None:
        """Recursively traverse directories up to max_depth."""
        if current_depth > max_depth:
            return

        try:
            for item in current_path.iterdir():
                if should_ignore_name(item.name):
                    continue

                # [DL-WARN] Symlink escape guard: silently drops any symlink whose resolved target lies outside root_path.
                if item.is_symlink():
                    try:
                        item_resolved = item.resolve()
                        if not _is_within_root(item_resolved):
                            continue
                    except OSError:
                        continue
                    post_fix = "/" if item_resolved.is_dir() else ""
                    # [DL-NOTE] Appends the resolved target path, not the symlink name itself; symlink names are erased from the listing.
                    result.append(str(item_resolved) + post_fix)
                    continue

                item_resolved = item.resolve()
                if not _is_within_root(item_resolved):
                    continue

                post_fix = "/" if item.is_dir() else ""
                result.append(str(item_resolved) + post_fix)

                # Recurse into subdirectories if not at max depth
                if item.is_dir() and current_depth < max_depth:
                    _traverse(item, current_depth + 1)
        except PermissionError:
            pass

    # [DL-NOTE] Depth starts at 1, not 0; max_depth=2 yields direct children (depth 1) and their children (depth 2).
    _traverse(root_path, 1)

    # [DL-WARN] this does not handle file deduplication
    return sorted(result)
