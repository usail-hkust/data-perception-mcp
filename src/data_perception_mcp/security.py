from pathlib import Path


def validate_roots(paths: list[str]) -> tuple[Path, ...]:
    roots = tuple(Path(p).expanduser().resolve(strict=True) for p in paths)
    if any(not root.is_dir() for root in roots):
        raise ValueError("Every --allow-dir must be an existing directory")
    return roots


def validate_path(path: str, allowed_roots: tuple[Path, ...], max_bytes: int) -> Path:
    if not allowed_roots:
        raise PermissionError("No data directories authorized. Configure --allow-dir first.")
    resolved = Path(path).expanduser().resolve(strict=True)
    if not any(resolved.is_relative_to(root.resolve()) for root in allowed_roots):
        raise PermissionError("The requested path is outside the allowed directories.")
    if not resolved.is_file():
        raise ValueError("data_path must refer to a regular file")
    if resolved.stat().st_size > max_bytes:
        raise ValueError(f"File exceeds the configured {max_bytes}-byte limit")
    return resolved
