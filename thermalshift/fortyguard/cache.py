"""Deterministic local cache for successful FortyGuard heatmap results."""

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from thermalshift.fortyguard.models import HeatmapResult

CACHE_SCHEMA_VERSION = 1
DEFAULT_CACHE_DIRECTORY = Path("data/cache/fortyguard")
_SENSITIVE_KEYS = frozenset({"api-key", "api_key", "authorization", "credentials", "headers"})


class FortyGuardCacheError(RuntimeError):
    """Raised when a cache payload is unsafe, corrupt, or incompatible."""


def canonical_payload_json(payload: Mapping[str, Any]) -> str:
    """Serialize a complete request payload with stable ordering and separators."""
    _reject_sensitive_keys(payload)
    try:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise FortyGuardCacheError("Request payload is not canonical JSON data") from exc


def cache_key_for_payload(payload: Mapping[str, Any]) -> str:
    """Return the SHA-256 digest of a canonical complete request payload."""
    return hashlib.sha256(canonical_payload_json(payload).encode()).hexdigest()


class HeatmapResultCache:
    """Filesystem cache containing validated successful heatmap results."""

    def __init__(self, directory: str | Path = DEFAULT_CACHE_DIRECTORY) -> None:
        self.directory = Path(directory)

    def contains(self, payload: Mapping[str, Any]) -> bool:
        """Return whether a cache file exists without parsing it."""
        return self._path(payload).is_file()

    def get(self, payload: Mapping[str, Any]) -> HeatmapResult | None:
        """Return a validated cached result, or None for a cache miss."""
        key = cache_key_for_payload(payload)
        path = self.directory / f"{key}.json"
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FortyGuardCacheError(f"Could not read valid cache JSON: {path}") from exc

        if (
            not isinstance(record, dict)
            or record.get("cache_schema_version") != CACHE_SCHEMA_VERSION
        ):
            raise FortyGuardCacheError(f"Unsupported or malformed cache record: {path}")
        request_payload = record.get("request_payload")
        if not isinstance(request_payload, dict) or cache_key_for_payload(request_payload) != key:
            raise FortyGuardCacheError(f"Cache request payload does not match its key: {path}")
        try:
            return HeatmapResult.model_validate(record.get("heatmap_result"))
        except ValidationError as exc:
            raise FortyGuardCacheError(f"Cache contains an invalid heatmap result: {path}") from exc

    def put(self, payload: Mapping[str, Any], result: HeatmapResult) -> Path:
        """Atomically store a validated successful result and audit metadata."""
        validated_result = HeatmapResult.model_validate(result)
        key = cache_key_for_payload(payload)
        path = self.directory / f"{key}.json"
        record = {
            "cache_schema_version": CACHE_SCHEMA_VERSION,
            "request_payload": dict(payload),
            "heatmap_result": validated_result.model_dump(mode="json"),
        }
        try:
            serialized = json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n"
        except (TypeError, ValueError) as exc:
            raise FortyGuardCacheError("Cache record is not valid JSON data") from exc

        self.directory.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.directory,
                prefix=f".{key}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(serialized)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            temporary_path.replace(path)
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise FortyGuardCacheError(f"Could not write cache record: {path}") from exc
        return path

    def _path(self, payload: Mapping[str, Any]) -> Path:
        return self.directory / f"{cache_key_for_payload(payload)}.json"


def _reject_sensitive_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str) and key.casefold() in _SENSITIVE_KEYS:
                raise FortyGuardCacheError(
                    "Request payload must not contain credentials or headers"
                )
            _reject_sensitive_keys(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_sensitive_keys(child)
