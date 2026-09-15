# data-perception-mcp

**Turn a local dataset into inspectable Data Context for an AI assistant.**

Data Perception is a Python MCP server that profiles authorized local files and returns a text Tool Result. It can optionally use a local Hugging Face-compatible language model to interpret the observations for a requested task.

[中文说明](#中文说明) · [Model setup](docs/models.md) · [Publishing](docs/publishing.md)

## Current status

- **Available:** deterministic data profiling, STDIO MCP, directory allowlists, Codex registration, local/Hugging Face model configuration, and a Transformers inference adapter.
- **Model weights are not published with this repository.** No model ID is assumed and nothing is downloaded in the default `profile` mode.
- **PyPI publication is pending.** Use the GitHub installation below today. The shorter PyPI commands become applicable only after the package is published.
- The inference adapter has not been validated against the planned 4B model. Its architecture, chat template, memory requirements, and output quality still need validation after the weights are available.

## Quick start: install from GitHub

Prerequisites: Git, Python 3.10+, [uv](https://docs.astral.sh/uv/getting-started/installation/), and a working Codex CLI on your `PATH`. Create or choose a data directory before installation.

```bash
# Install uv if needed
python -m pip install uv

# Register the server with Codex; replace this with your dataset directory
uvx --from git+https://github.com/usail-hkust/data-perception-mcp.git \
  data-perception-mcp install --allow-dir "$HOME/datasets"

# Confirm registration
codex mcp list
```

Use repeated `--allow-dir` flags to authorize multiple directories. Installation fails if a directory does not exist. The installer registers the same GitHub package source for future launches, so it does not depend on a PyPI release. It changes Codex configuration only when `install` is invoked; `serve` does not install anything.

Restart the client if the newly added tool does not appear. Then ask:

> Use `build_data_context` to inspect `/absolute/path/to/datasets/train.csv` for customer churn prediction. Distinguish observed facts from hypotheses.

Preview the exact registration command without changing configuration:

```bash
uvx --from git+https://github.com/usail-hkust/data-perception-mcp.git \
  data-perception-mcp install --allow-dir "$HOME/datasets" --dry-run
```

Codex's `mcp add <name> -- <command>` syntax follows the [official MCP configuration documentation](https://developers.openai.com/codex/mcp).

### Direct registration

```bash
codex mcp add data-perception -- \
  uvx --from git+https://github.com/usail-hkust/data-perception-mcp.git \
  data-perception-mcp serve --allow-dir "$HOME/datasets"
```

### Try the included sample locally

```bash
git clone https://github.com/usail-hkust/data-perception-mcp.git
cd data-perception-mcp
uv run data-perception-mcp install --allow-dir "$PWD/examples" --dry-run
uv run data-perception-mcp serve --allow-dir "$PWD/examples"
```

`serve` waits for MCP messages on standard input; it is not an interactive terminal prompt. The fixture `examples/customers.csv` is synthetic. Use its absolute path in the tool call.

## Tool interface

```text
build_data_context(task: str, data_path: str)
```

| Argument | Meaning |
| --- | --- |
| `task` | Non-empty analysis request, at most 4,000 characters |
| `data_path` | Path to one existing local file under an authorized directory |

Successful calls return an explicit SDK `CallToolResult`:

```json
{
  "content": [
    { "type": "text", "text": "# Data Context\n..." }
  ],
  "isError": false
}
```

The response has no `structuredContent`; JSON-RPC envelopes are managed by the MCP SDK. Failed calls return `isError: true` with a diagnostic text block. Dependencies write diagnostic output to stderr during tool execution, keeping stdout for the MCP transport.

See a [complete generated example](docs/example-context.md) using the synthetic customer fixture.

### What the context contains

1. The requested task and source filename.
2. Per-table row coverage, source column count, inferred dtypes, missing values, distinct counts, numeric min/max/mean, and duplicate counts.
3. Explicit row, column, and table truncation indicators.
4. Interpretation limits and checks for grain, target definition, time ordering, keys, and leakage.
5. Optional model interpretation, clearly labeled as unverified; deterministic evidence is retained verbatim.

Default mode includes the task but does **not** perform learned task-specific reasoning. Its next-check section is a generic checklist. The model backend adds task-specific interpretation when configured.

## Supported data

| Format | Behavior |
| --- | --- |
| CSV / TSV | UTF-8, header row; first configured rows |
| JSON | Array of record objects; whole file parsed before taking first rows |
| JSONL / NDJSON | One record per line; first configured rows |
| Parquet | First row batch |
| Excel `.xlsx` | First configured sheets and rows; first row is the header; cached formula values only |
| SQLite `.sqlite`, `.sqlite3`, `.db` | Read-only connection; first ordinary tables alphabetically; no user SQL, views, or virtual tables |

Excel columns are labeled with their index and header (`0:customer_id`) to preserve duplicate header identity. CSV duplicate headers follow pandas parsing conventions. Nested JSON values are canonicalized for distinct and duplicate counting.

### Coverage and limits

| Option | Default |
| --- | --- |
| `--max-rows` | 1,000 per table |
| `--max-columns` | 100 per table |
| `--max-tables` | 10 per workbook/database |
| `--max-file-bytes` | 20,971,520 (20 MiB) |
| `--max-input-tokens` | 4,096 for model input |
| `--max-new-tokens` | 1,024 for model output |

The first rows are **not a random sample**. Counts, missingness, ranges, and means describe analyzed rows only. Duplicate counts use analyzed columns only. Exact total row counts are not computed when truncated. SQLite row order is unspecified without an application-defined ordering.

File-size and row limits reduce resource use but are not a hard memory/CPU sandbox. JSON is parsed in full, compressed data may expand, and wide rows may require substantial memory before column clipping. XLSX additionally checks advertised uncompressed ZIP size. For untrusted hostile inputs, run the process in an OS/container sandbox with memory and time limits.

## Optional model backend

Use `--backend transformers` with **one** of:

- `--model-path /absolute/path/to/model`: load a local model directory.
- `--model-repo ORGANIZATION/MODEL`: download a model snapshot on the first tool call.

The adapter requires a Transformers-supported causal language model with a usable chat template and safetensors weights. It does not run arbitrary repository Python code. GGUF/llama.cpp is a future extension, not currently implemented.

```bash
# Replace MODEL_PATH with your actual local model directory
uvx --from 'data-perception-mcp[model] @ git+https://github.com/usail-hkust/data-perception-mcp.git' \
  data-perception-mcp install \
  --allow-dir "$HOME/datasets" \
  --backend transformers --model-path /absolute/path/to/MODEL_PATH
```

See [model setup](docs/models.md) for Hugging Face downloads, revision pinning, prefetching, and operational limits.

## Privacy and access

- No allowed roots means no dataset access. `install` requires at least one existing directory.
- Paths are resolved before checking containment, rejecting ordinary traversal and symlinks that resolve outside allowed roots.
- Dataset access is read-only. No dataset-provided Python or SQL is executed.
- Raw example rows are omitted. Column/table names and numeric aggregates can still reveal sensitive information and are returned to the MCP client. The client's data policies govern what happens next.
- Default profiling makes no model-network calls. Explicit Hugging Face setup downloads weights; inference runs locally. The package contains no telemetry.
- The allowlist is an application check, not OS isolation. It does not defend against another local process changing paths between validation and reading. Authorize stable directories you control.

## Update and remove

Refresh from GitHub and register again with the desired allowed directories:

```bash
uvx --refresh --from git+https://github.com/usail-hkust/data-perception-mcp.git \
  data-perception-mcp install --allow-dir "$HOME/datasets"

codex mcp remove data-perception
```

Re-registration uses the supplied options; repeat all directories and model options you want to retain. Removing the registration does not delete uv environments, datasets, or downloaded model caches. For reproducible deployments use a full Git commit in the package URL and pass that same URL to `install --package`.

### After PyPI publication

These commands are **not the current installation path**:

```bash
uvx data-perception-mcp install \
  --package data-perception-mcp --allow-dir "$HOME/datasets"

# Model-enabled installation after publication
uvx --from 'data-perception-mcp[model]' data-perception-mcp install \
  --package 'data-perception-mcp[model]' \
  --allow-dir "$HOME/datasets" --backend transformers \
  --model-path /absolute/path/to/model
```

The explicit `--package` chooses what Codex will launch later. Without it, the installer defaults to GitHub, including model dependencies when the Transformers backend is selected.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
pytest -q
python -m build
python -m twine check dist/*
```

Tests cover supported readers, statistics and truncation, path restrictions, installation arguments, mocked download behavior, and an actual STDIO client/server exchange. They do not establish quality or hardware compatibility for the unpublished model. CI runs these checks on Python 3.10 and 3.12.

```text
src/data_perception_mcp/
├── cli.py            # Server, installation, model download commands
├── config.py         # Runtime settings and validation
├── server.py         # MCP Tool Result and STDIO transport
├── agent.py          # Evidence assembly and optional interpretation
├── profiling.py      # File readers and descriptive statistics
├── security.py       # Dataset path admission
├── model_manager.py  # Local paths / Hugging Face snapshots
└── runtime.py        # Lazy Transformers inference
```

See [publishing](docs/publishing.md) for the GitHub / PyPI / Hugging Face release sequence.

## 中文说明

本项目把本地数据文件转换为可供 AI 助手使用的 **Data Context**，通过 MCP 返回标准的 `content: [{"type": "text", ...}]`，成功时 `isError: false`。

### 当前能做什么

- 支持 CSV、TSV、JSON、JSONL、Parquet、Excel XLSX 和 SQLite。
- 提供字段类型、缺失值、不同值数量、数值范围、均值和重复行概况。
- 默认分析每张表前 1,000 行，并明确说明截断范围，不能当作完整数据集统计。
- 只允许读取 `--allow-dir` 授权的目录；不指定目录就不能读取数据。
- 支持一条命令注册到 Codex，支持安装命令预览。
- 已实现可选的 Transformers 本地推理适配器，可从本地路径或 Hugging Face 加载兼容模型。

**目前 4B 模型尚未发布，PyPI 发布也尚未完成。** 默认模式不调用模型；它生成可检查的数据概况和通用核查清单，不代表 4B Agent 已完成深度分析。当前版本是根据需求说明实现的初版，不包含未提供的原始 Agent 源码或权重。

### 现在就能安装

先安装 uv，并确保 Codex CLI 可用，然后执行：

```bash
uvx --from git+https://github.com/usail-hkust/data-perception-mcp.git \
  data-perception-mcp install --allow-dir "$HOME/datasets"
```

将目录替换成真实存在的数据目录。多个目录重复使用 `--allow-dir`。检查：`codex mcp list`；卸载注册：`codex mcp remove data-perception`。

### 发布关系

| 内容 | 位置 | 当前状态 |
| --- | --- | --- |
| MCP 源码、说明、测试 | GitHub | 本仓库提供 |
| Python 安装包 | PyPI | 待发布，暂时从 GitHub 安装 |
| 4B 模型权重、tokenizer、模板 | Hugging Face | 待上传 |
| GGUF 量化运行时 | 后续扩展 | 尚未实现 |

模型准备好后，按 [模型接入说明](docs/models.md) 设置真实仓库 ID 或本地路径，再验证模型架构、聊天模板、内存需求和分析质量。模型权重不应打包到 PyPI 或提交进本仓库。

## License

MIT for the code in this repository. Model weights and datasets retain their own licenses.
