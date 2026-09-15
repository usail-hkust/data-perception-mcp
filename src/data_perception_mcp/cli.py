import argparse
import shlex
import shutil
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

from .config import Settings
from .model_manager import resolve_model
from .security import validate_roots

SOURCE = "git+https://github.com/usail-hkust/data-perception-mcp.git"


def add_options(parser):
    parser.add_argument("--allow-dir", action="append", default=[], metavar="DIRECTORY")
    parser.add_argument("--backend", choices=["profile", "transformers"], default="profile")
    model = parser.add_mutually_exclusive_group()
    model.add_argument("--model-path")
    model.add_argument("--model-repo")
    parser.add_argument("--revision", help="Hugging Face revision; a commit hash is recommended")
    parser.add_argument("--cache-dir")
    for name in (
        "max_rows",
        "max_file_bytes",
        "max_columns",
        "max_tables",
        "max_new_tokens",
        "max_input_tokens",
    ):
        parser.add_argument(
            "--" + name.replace("_", "-"), type=int, default=getattr(Settings(), name)
        )


def to_settings(args):
    data = {
        field.name: getattr(args, field.name)
        for field in fields(Settings)
        if field.name != "allowed_roots"
    }
    for key in ("model_path", "cache_dir"):
        if data[key]:
            data[key] = str(Path(data[key]).expanduser().resolve())
    return Settings(allowed_roots=validate_roots(args.allow_dir), **data)


def registration_command(args, settings):
    package = args.package
    if not package:
        package = (
            "data-perception-mcp[model] @ " + SOURCE
            if settings.backend == "transformers"
            else SOURCE
        )
    command = [
        "codex",
        "mcp",
        "add",
        args.name,
        "--",
        "uvx",
        "--from",
        package,
        "data-perception-mcp",
        "serve",
    ]
    for root in settings.allowed_roots:
        command.extend(["--allow-dir", str(root)])
    for field in fields(Settings):
        if field.name == "allowed_roots":
            continue
        value = getattr(settings, field.name)
        if value is not None:
            command.extend(["--" + field.name.replace("_", "-"), str(value)])
    return command


def main(argv=None):
    parser = argparse.ArgumentParser(description="Data Perception MCP server and Codex installer")
    sub = parser.add_subparsers(dest="command", required=True)
    add_options(sub.add_parser("serve", help="Run the STDIO MCP server (default)"))
    install = sub.add_parser("install", help="Register this server with Codex")
    add_options(install)
    install.add_argument("--name", default="data-perception")
    install.add_argument("--package", help="uv package specifier to register; defaults to GitHub")
    install.add_argument("--download-model", action="store_true")
    install.add_argument(
        "--dry-run", action="store_true", help="Print command without changing configuration"
    )
    download = sub.add_parser("download-model", help="Download configured model weights only")
    add_options(download)
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or (argv[0].startswith("--") and argv[0] not in {"--help"}):
        argv.insert(0, "serve")
    args = parser.parse_args(argv)
    try:
        settings = to_settings(args)
        if args.command == "serve":
            from .server import run

            run(settings)
        elif args.command == "download-model":
            print(resolve_model(settings))
        else:
            if not settings.allowed_roots:
                raise ValueError("Installation requires at least one --allow-dir")
            command = registration_command(args, settings)
            if args.download_model and not (settings.model_path or settings.model_repo):
                raise ValueError("--download-model requires --model-path or --model-repo")
            if args.dry_run:
                print(shlex.join(command))
                return
            for executable in ("codex", "uvx"):
                if not shutil.which(executable):
                    raise ValueError(f"{executable} is not on PATH; install it before registration")
            if args.download_model:
                resolve_model(settings)
            subprocess.run(command, check=True)
            print("Registered. Restart the client if needed; verify with: codex mcp list")
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")
