# Model setup

The project does not ship a model or assume a published repository ID. The default `profile` backend works without weights or GPU dependencies.

## Supported adapter

The `transformers` backend loads `AutoTokenizer` and `AutoModelForCausalLM` locally, renders the model's chat template, and generates an interpretation of the deterministic profile. It is a single generation adapter, not a recreation of an unpublished multi-step Data Perception Agent.

Requirements:

- A causal model architecture supported by Transformers 4.x.
- Safetensors weights, `config.json`, tokenizer assets, and a tokenizer chat template.
- A chat template accepting system and user messages.
- Sufficient RAM/VRAM for weights, activations, and the context; `device_map="auto"` handles placement but is not a guarantee that the model fits.

`trust_remote_code=False` and `use_safetensors=True` are enforced. Custom-code architectures, pickle-only weights, and GGUF files are not supported. No hardware compatibility claim has yet been validated for the planned 4B model.

## Local model

```bash
uvx --from 'data-perception-mcp[model] @ git+https://github.com/usail-hkust/data-perception-mcp.git' \
  data-perception-mcp install --allow-dir "$HOME/datasets" \
  --backend transformers --model-path /absolute/path/to/model
```

Model files are loaded lazily on first use and retained in process memory. Requests are serialized to avoid concurrent model loads.

## Hugging Face model

Replace `YOUR_ORG/YOUR_MODEL` and `MODEL_COMMIT` with real values after uploading the model:

```bash
uvx --from 'data-perception-mcp[model] @ git+https://github.com/usail-hkust/data-perception-mcp.git' \
  data-perception-mcp install --allow-dir "$HOME/datasets" \
  --backend transformers --model-repo YOUR_ORG/YOUR_MODEL \
  --revision MODEL_COMMIT --cache-dir "$HOME/.cache/data-perception" \
  --download-model
```

`--download-model` downloads during installation. Omit it to download on first tool use. Downloading requires network access and several GB may be needed. Prefetching does not validate model loading or inference. Authentication for gated/private models follows the Hugging Face Hub configuration on the machine running the server; credentials are not written into this project's registration arguments.

To prefetch without registering with Codex:

```bash
uvx --from git+https://github.com/usail-hkust/data-perception-mcp.git \
  data-perception-mcp download-model \
  --model-repo YOUR_ORG/YOUR_MODEL --revision MODEL_COMMIT
```

The download allowlist includes JSON, safetensors, tokenizer `.model`, `.txt`, and `.tiktoken` assets. Architectures requiring other assets need an explicit implementation update.

## Token budgets and timeouts

Input beyond `--max-input-tokens` is rejected rather than silently truncated. Reduce `--max-columns` and `--max-tables` for wide datasets. Generation stops at `--max-new-tokens`, so generated interpretation can be incomplete; the full deterministic profile remains in the returned text.

A first download, model load, or CPU generation may exceed the MCP client's tool timeout. Prefetch weights, benchmark locally, and set a suitable `tool_timeout_sec` for the server in Codex configuration if needed. The process does not enforce a hard inference timeout and cancellation may leave a worker thread finishing its computation. Use process supervision for strict runtime limits.

## Before announcing the 4B model

1. Upload weights, configuration, tokenizer, chat template, model card, and model license to an actual Hugging Face repository.
2. Pin an immutable model revision and verify that loading succeeds without remote Python code.
3. Run the tool against representative files, including empty, wide, missing-value, and malformed inputs.
4. Check that interpretations cite observed evidence, respect truncation, and do not invent target semantics.
5. Publish measured hardware requirements and first-call versus warm-call latency.
6. Update README examples with the verified model ID and revision.

References: [Transformers text generation](https://huggingface.co/docs/transformers/main/en/llm_tutorial), [Hub downloads](https://huggingface.co/docs/huggingface_hub/guides/download).
