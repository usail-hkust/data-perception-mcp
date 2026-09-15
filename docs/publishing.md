# Publishing and maintenance

Source, Python package, and weights have separate release lifecycles. A public GitHub repository does not imply that a package or model has been published elsewhere.

## 1. GitHub

Run tests and distribution checks before pushing:

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest -q
python -m build
python -m twine check dist/*
```

The repository CI repeats these checks. Keep secrets, private datasets, model weights, and virtual environments out of commits. The example CSV is synthetic.

For a reproducible installation, use the full reviewed Git commit:

```bash
uvx --from git+https://github.com/usail-hkust/data-perception-mcp.git@GIT_COMMIT \
  data-perception-mcp install --allow-dir /absolute/path/to/datasets \
  --package git+https://github.com/usail-hkust/data-perception-mcp.git@GIT_COMMIT
```

Both occurrences of `GIT_COMMIT` must be replaced. For model deployments pass a PEP 508 package specifier including `[model]` to both `--from` and `--package`.

## 2. PyPI (pending)

Confirm ownership/availability of `data-perception-mcp` on PyPI, choose a release version in `pyproject.toml` and `__init__.py`, and build from a clean checkout. Use an account-controlled API token or configure PyPI Trusted Publishing. This repository does not automatically publish packages.

```bash
python -m build
python -m twine check dist/*
# Maintainer action: uploads the built release artifacts
python -m twine upload dist/*
```

Do not reuse a version already uploaded to PyPI. Ensure `dist/` contains only the intended release. Validate installation in a fresh environment before changing the README status:

```bash
uvx --from data-perception-mcp==VERSION data-perception-mcp --help
uvx --from data-perception-mcp==VERSION data-perception-mcp install \
  --package data-perception-mcp==VERSION \
  --allow-dir /absolute/path/to/datasets --dry-run
```

## 3. Hugging Face (pending)

Publish weights separately, with architecture/configuration, tokenizer, chat template, model card, usage examples, evaluation limitations, and license. See [model setup](models.md). Do not put weights in wheels or source distributions.

GGUF may be published as a separate model artifact, but the current server does not include a llama.cpp backend. Do not advertise GGUF inference until the adapter and installation path have been implemented and verified.

## 4. Release verification

- Install from the actual distribution source in a fresh environment.
- Check `install --dry-run` retains allowed directories, backend, source, and model revision.
- Register on a machine with a working Codex CLI and uvx, then inspect `codex mcp list`.
- Make an actual MCP call and confirm a text result with `isError: false`.
- Verify unauthorized paths produce `isError: true`.
- For model releases, separately benchmark actual inference and accuracy.

References: [Python package publishing](https://packaging.python.org/en/latest/tutorials/packaging-projects/), [Codex MCP](https://developers.openai.com/codex/mcp), [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
