import json

from .config import Settings
from .profiling import profile
from .runtime import ModelRuntime
from .security import validate_path


class PerceptionAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.runtime = ModelRuntime(settings) if settings.backend == "transformers" else None

    def build_context(self, task: str, data_path: str) -> str:
        if not task.strip() or len(task) > 4000:
            raise ValueError("task must contain 1–4000 characters")
        path = validate_path(data_path, self.settings.allowed_roots, self.settings.max_file_bytes)
        observations = profile(path, self.settings)
        evidence = json.dumps(observations, ensure_ascii=False, indent=2, allow_nan=False)
        context = (
            "# Data Context\n\n"
            f"## Requested task\n{task}\n\n"
            f"## Observations\n```json\n{evidence}\n```\n\n"
            "## Interpretation limits\n"
            "Statistics cover only the first configured rows and columns. Duplicate counts use "
            "only analyzed columns. Column types are reader-inferred, not semantic definitions. "
            "No raw example rows are included. Aggregate values and column names can still be sensitive.\n\n"
            "## Next checks\n"
            "Confirm the unit of observation, target definition, time ordering, join keys, and "
            "possible target leakage against the requested task. Confirm sample representativeness "
            "before generalizing. These are checks to perform, not established findings.\n"
        )
        if self.runtime:
            return (
                context
                + "\n## Model interpretation (unverified)\n"
                + self.runtime.generate(context)
            )
        return context + "\nMode: deterministic profile; no model inference was performed.\n"
