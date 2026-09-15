"""Exercise adapter wiring without downloading the unpublished model."""

import sys
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from data_perception_mcp.config import Settings
from data_perception_mcp.runtime import ModelRuntime


class Inputs(dict):
    def __init__(self, size):
        super().__init__(input_ids=SimpleNamespace(shape=(1, size)))

    def to(self, device):
        return self


class Output:
    def __getitem__(self, key):
        assert key[1].start == 4
        return [9, 10]


def test_inference_adapter(monkeypatch, tmp_path):
    tokenizer = Mock()
    tokenizer.apply_chat_template.return_value = "rendered prompt"
    tokenizer.return_value = Inputs(4)
    tokenizer.decode.return_value = "Model interpretation"
    tokenizer.eos_token_id = 2
    model = Mock()
    model.config.max_position_embeddings = 100
    model.device = "cpu"
    model.generate.return_value = Output()
    tokenizer_class = SimpleNamespace(from_pretrained=Mock(return_value=tokenizer))
    model_class = SimpleNamespace(from_pretrained=Mock(return_value=model))
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(inference_mode=nullcontext))
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        SimpleNamespace(
            AutoTokenizer=tokenizer_class,
            AutoModelForCausalLM=model_class,
        ),
    )
    runtime = ModelRuntime(
        Settings(backend="transformers", model_path=str(tmp_path), max_new_tokens=10)
    )
    assert runtime.generate("Evidence") == "Model interpretation"
    assert runtime.generate("More evidence") == "Model interpretation"
    model_class.from_pretrained.assert_called_once()
    assert model_class.from_pretrained.call_args.kwargs["trust_remote_code"] is False
    assert model_class.from_pretrained.call_args.kwargs["use_safetensors"] is True
    assert model.generate.call_args.kwargs["max_new_tokens"] == 10
    assert model.generate.call_args.kwargs["do_sample"] is False
    tokenizer.return_value = Inputs(5000)
    with pytest.raises(ValueError, match="token limit"):
        runtime.generate("oversized")
    tokenizer.return_value = Inputs(95)
    with pytest.raises(ValueError, match="context window"):
        runtime.generate("too large for model")
