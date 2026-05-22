"""Config utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union
import os

import yaml


def load_config(path: Union[str, Path]) -> Dict[str, Any]:
    p = Path(path)
    data: Dict[str, Any] = {}
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return _expand_env_vars(data)


def _expand_env_vars(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env_vars(v) for v in obj]
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    return obj
