"""Deterministic model routing, budget estimation, and config validation."""
from __future__ import annotations

import copy
import re
from typing import Any

TIERS = ("cheap", "current", "strong")
ROLES = ("implementer", "reviewer")
QUALITIES = ("actual", "calculated", "estimated", "unknown")
SOURCES = ("host", "worker", "configured-price", "heuristic", "unknown")
RISK = ("low", "medium", "high")
COMPLEXITY = ("simple", "normal", "complex")
ALLOWED_PLACEHOLDERS = {
    "{prompt_path}", "{model_id}", "{brief_path}", "{report_path}",
    "{task_id}", "{role}", "{operation_id}", "{project_root}",
}
# Prefix of the model IDs `sia orchestrate example` emits for the user to replace.
PLACEHOLDER_MODEL_PREFIX = "replace-with-"

DEFAULTS: dict[str, Any] = {
    "budget": {
        "max_tokens": 1_000_000,
        "max_cost_usd": 100.0,
        "warning_fraction": 0.8,
    },
    "concurrency": {"global": 4, "cheap": 4, "current": 2, "strong": 1},
    "routing": {
        "low": "cheap",
        "normal": "current",
        "high": "strong",
        "review": "current",
        "escalation": ["cheap", "current", "strong"],
    },
    "allow_model_fallback": False,
    "timeout_seconds": 900,
    "max_output_bytes": 1_000_000,
    "workers": {},
}


class RoutingError(ValueError):
    """Invalid routing, model, worker, or telemetry configuration."""


def _positive_number(value: Any, name: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RoutingError(f"{name} must be numeric")
    minimum = 0 if allow_zero else 0.0000001
    if value < minimum:
        raise RoutingError(f"{name} must be {'non-negative' if allow_zero else 'positive'}")
    return float(value)


def validate_orchestration_config(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise RoutingError("orchestration config must be a JSON object")
    config = copy.deepcopy(DEFAULTS)
    for key in DEFAULTS:
        if key in raw:
            if isinstance(DEFAULTS[key], dict):
                if not isinstance(raw[key], dict):
                    raise RoutingError(f"{key} must be an object")
                config[key].update(copy.deepcopy(raw[key]))
            else:
                config[key] = copy.deepcopy(raw[key])

    models = raw.get("models")
    if not isinstance(models, dict):
        raise RoutingError("models must define explicit cheap and current model IDs")
    normalized_models: dict[str, dict[str, Any]] = {}
    for tier in TIERS:
        if tier not in models:
            raise RoutingError(f"models.{tier} is required; strong may intentionally reuse current only when configured explicitly")
    for tier in TIERS:
        source = models[tier]
        if not isinstance(source, dict) or not isinstance(source.get("id"), str) or not source["id"].strip():
            raise RoutingError(f"models.{tier}.id must be a non-empty provider model ID")
        # `sia orchestrate example` emits deliberate placeholders. Accepting one
        # yields a config that validates and reports "configured": true, yet
        # cannot dispatch — the failure then surfaces far from its cause.
        if source["id"].strip().startswith(PLACEHOLDER_MODEL_PREFIX):
            raise RoutingError(
                f"models.{tier}.id is still the placeholder '{source['id'].strip()}'. "
                "Replace every placeholder with an exact provider model ID before "
                "configuring; SIA never guesses a model."
            )
        normalized_models[tier] = {
            "id": source["id"].strip(),
            "input_usd_per_million": _positive_number(
                source.get("input_usd_per_million", 0), f"models.{tier}.input_usd_per_million", allow_zero=True
            ),
            "output_usd_per_million": _positive_number(
                source.get("output_usd_per_million", 0), f"models.{tier}.output_usd_per_million", allow_zero=True
            ),
        }
    config["models"] = normalized_models

    budget = config["budget"]
    budget["max_tokens"] = int(_positive_number(budget.get("max_tokens"), "budget.max_tokens"))
    budget["max_cost_usd"] = _positive_number(budget.get("max_cost_usd"), "budget.max_cost_usd")
    warning = _positive_number(budget.get("warning_fraction"), "budget.warning_fraction")
    if warning >= 1:
        raise RoutingError("budget.warning_fraction must be less than 1")
    budget["warning_fraction"] = warning

    concurrency = config["concurrency"]
    for key in ("global", *TIERS):
        concurrency[key] = int(_positive_number(concurrency.get(key), f"concurrency.{key}"))

    routing = config["routing"]
    for key in ("low", "normal", "high", "review"):
        if routing.get(key) not in TIERS:
            raise RoutingError(f"routing.{key} must be one of: {', '.join(TIERS)}")
    escalation = routing.get("escalation")
    if not isinstance(escalation, list) or not escalation or any(tier not in TIERS for tier in escalation):
        raise RoutingError("routing.escalation must be a non-empty list of model tiers")
    routing["escalation"] = list(dict.fromkeys(escalation))

    if not isinstance(config.get("allow_model_fallback"), bool):
        raise RoutingError("allow_model_fallback must be boolean")
    config["timeout_seconds"] = int(_positive_number(config.get("timeout_seconds"), "timeout_seconds"))
    config["max_output_bytes"] = int(_positive_number(config.get("max_output_bytes"), "max_output_bytes"))

    workers = config.get("workers", {})
    if not isinstance(workers, dict):
        raise RoutingError("workers must be an object")
    normalized_workers: dict[str, dict[str, Any]] = {}
    for name, worker in workers.items():
        if name not in (*TIERS, "default"):
            raise RoutingError(f"unsupported worker key {name!r}; use a tier or 'default'")
        if not isinstance(worker, dict):
            raise RoutingError(f"workers.{name} must be an object")
        argv = worker.get("argv")
        if not isinstance(argv, list) or not argv or any(not isinstance(value, str) or not value for value in argv):
            raise RoutingError(f"workers.{name}.argv must be a non-empty string array")
        if "{" in argv[0] or "}" in argv[0]:
            raise RoutingError(f"workers.{name}.argv[0] must be a fixed executable")
        for value in argv[1:]:
            if ("{" in value or "}" in value) and value not in ALLOWED_PLACEHOLDERS:
                raise RoutingError(
                    f"workers.{name} placeholder must occupy a whole argument; allowed: {sorted(ALLOWED_PLACEHOLDERS)}"
                )
        env_allow = worker.get("env_allow", [])
        if not isinstance(env_allow, list) or any(
            not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) for value in env_allow
        ):
            raise RoutingError(f"workers.{name}.env_allow must contain environment variable names only")
        normalized_workers[name] = {
            "argv": argv,
            "env_allow": list(dict.fromkeys(env_allow)),
            "timeout_seconds": int(_positive_number(
                worker.get("timeout_seconds", config["timeout_seconds"]), f"workers.{name}.timeout_seconds"
            )),
            "max_output_bytes": int(_positive_number(
                worker.get("max_output_bytes", config["max_output_bytes"]), f"workers.{name}.max_output_bytes"
            )),
        }
    config["workers"] = normalized_workers
    return config


def route_task(task: dict[str, Any], role: str, config: dict[str, Any]) -> tuple[str, str]:
    if role not in ROLES:
        raise RoutingError(f"unsupported role: {role}")
    if role == "reviewer":
        tier = "strong" if task.get("risk") == "high" else config["routing"]["review"]
        return tier, "independent review" + (" of high-risk work" if task.get("risk") == "high" else "")
    risk = task.get("risk", "medium")
    complexity = task.get("complexity", "normal")
    if risk == "high" or complexity == "complex":
        return config["routing"]["high"], f"{risk}-risk/{complexity} implementation"
    if risk == "low" and complexity == "simple":
        return config["routing"]["low"], "bounded low-risk/simple implementation"
    return config["routing"]["normal"], f"{risk}-risk/{complexity} implementation"


def estimate_tokens(task: dict[str, Any], role: str, brief_bytes: int) -> tuple[int, str]:
    supplied = task.get("estimated_tokens")
    if isinstance(supplied, int) and supplied > 0:
        base = supplied
        source = "user"
    else:
        base = max(2_000, brief_bytes // 4 + 2_000)
        source = "heuristic"
    if role == "reviewer":
        base = max(1_500, int(base * 0.55))
    return base, source


def estimate_cost(tokens: int, model: dict[str, Any]) -> float:
    input_tokens = int(tokens * 0.65)
    output_tokens = tokens - input_tokens
    return round(
        input_tokens * model["input_usd_per_million"] / 1_000_000
        + output_tokens * model["output_usd_per_million"] / 1_000_000,
        8,
    )


def normalize_telemetry(raw: Any, operation: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    input_tokens = raw.get("input_tokens")
    output_tokens = raw.get("output_tokens")
    actual_numbers = all(isinstance(value, int) and value >= 0 for value in (input_tokens, output_tokens))
    if actual_numbers:
        total = input_tokens + output_tokens
        cost = raw.get("cost_usd")
        if isinstance(cost, (int, float)) and cost >= 0:
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total,
                "cost_usd": round(float(cost), 8),
                "quality": "actual",
                "source": raw.get("source", "worker"),
            }
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total,
            "cost_usd": estimate_cost(total, model),
            "quality": "calculated",
            "source": "configured-price",
        }
    estimated = int(operation["estimated_tokens"])
    return {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": estimated,
        "cost_usd": float(operation["estimated_cost_usd"]),
        "quality": "estimated",
        "source": "heuristic",
    }


def example_config() -> dict[str, Any]:
    """Return a safe template with no executable worker configured."""
    return {
        "models": {
            "cheap": {"id": "replace-with-cheap-model-id", "input_usd_per_million": 0, "output_usd_per_million": 0},
            "current": {"id": "replace-with-selected-model-id", "input_usd_per_million": 0, "output_usd_per_million": 0},
            "strong": {"id": "replace-with-strong-model-id", "input_usd_per_million": 0, "output_usd_per_million": 0},
        },
        "budget": {"max_tokens": 500000, "max_cost_usd": 25, "warning_fraction": 0.8},
        "concurrency": {"global": 4, "cheap": 4, "current": 2, "strong": 1},
        "routing": {
            "low": "cheap", "normal": "current", "high": "strong",
            "review": "current", "escalation": ["cheap", "current", "strong"],
        },
        "allow_model_fallback": False,
        "timeout_seconds": 900,
        "max_output_bytes": 1000000,
        "workers": {},
    }
