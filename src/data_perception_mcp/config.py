from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    allowed_roots: tuple[Path, ...] = ()
    backend: str = "profile"
    model_path: str | None = None
    model_repo: str | None = None
    revision: str | None = None
    cache_dir: str | None = None
    max_rows: int = 1000
    max_file_bytes: int = 20 * 1024 * 1024
    max_columns: int = 100
    max_tables: int = 10
    max_new_tokens: int = 1024
    max_input_tokens: int = 4096

    def __post_init__(self):
        if self.backend not in {"profile", "transformers"}:
            raise ValueError("backend must be profile or transformers")
        if self.model_path and self.model_repo:
            raise ValueError("Choose model_path or model_repo, not both")
        if self.backend == "transformers" and not (self.model_path or self.model_repo):
            raise ValueError("transformers requires --model-path or --model-repo")
        for key in (
            "max_rows",
            "max_file_bytes",
            "max_columns",
            "max_tables",
            "max_new_tokens",
            "max_input_tokens",
        ):
            if getattr(self, key) <= 0:
                raise ValueError(f"{key} must be positive")
