from pathlib import Path

from .config import Settings


def resolve_model(settings: Settings) -> Path:
    if settings.model_path:
        path = Path(settings.model_path).expanduser().resolve(strict=True)
        if not path.is_dir():
            raise ValueError("--model-path must be a model directory")
        return path
    if not settings.model_repo:
        raise ValueError("No model configured; specify --model-path or --model-repo")
    from huggingface_hub import snapshot_download

    # No pickle weights or repository Python code. Remote code execution is disabled at load.
    return Path(
        snapshot_download(
            repo_id=settings.model_repo,
            revision=settings.revision,
            cache_dir=settings.cache_dir,
            allow_patterns=["*.json", "*.safetensors", "*.model", "*.txt", "*.tiktoken"],
        )
    )
