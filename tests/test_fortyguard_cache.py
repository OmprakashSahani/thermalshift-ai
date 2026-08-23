"""Tests for the local successful-result cache."""

import json
from pathlib import Path

import pytest

from tests.test_fortyguard_models import completed_data
from thermalshift.fortyguard.cache import (
    FortyGuardCacheError,
    HeatmapResultCache,
    cache_key_for_payload,
)
from thermalshift.fortyguard.models import HeatmapResult


def sample_result() -> HeatmapResult:
    return HeatmapResult.model_validate(completed_data()["result"])


def test_identical_payload_has_identical_key() -> None:
    left = {"b": [2, 3], "a": 1}
    right = {"a": 1, "b": [2, 3]}

    assert cache_key_for_payload(left) == cache_key_for_payload(right)


def test_changed_payload_has_different_key() -> None:
    assert cache_key_for_payload({"granularity": 100}) != cache_key_for_payload(
        {"granularity": 80}
    )


def test_put_get_round_trip_and_lazy_nested_directory(tmp_path: Path) -> None:
    directory = tmp_path / "nested" / "cache"
    cache = HeatmapResultCache(directory)
    payload = {"granularity": 100}

    assert not directory.exists()
    assert cache.get(payload) is None
    path = cache.put(payload, sample_result())

    assert directory.is_dir()
    assert path.suffix == ".json"
    assert cache.get(payload) == sample_result()


def test_miss_is_distinct_from_corrupt_cache(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    payload = {"granularity": 100}

    assert cache.get(payload) is None
    corrupt_path = tmp_path / f"{cache_key_for_payload(payload)}.json"
    corrupt_path.write_text("not json", encoding="utf-8")

    with pytest.raises(FortyGuardCacheError, match="valid cache JSON"):
        cache.get(payload)


def test_cache_record_contains_audit_data_but_no_credentials(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    path = cache.put({"granularity": 100}, sample_result())

    record = json.loads(path.read_text(encoding="utf-8"))
    serialized = json.dumps(record).casefold()
    assert record["cache_schema_version"] == 1
    assert record["request_payload"] == {"granularity": 100}
    assert "api-key" not in serialized
    assert "authorization" not in serialized
    assert "headers" not in serialized


def test_payload_with_sensitive_fields_is_rejected(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)

    with pytest.raises(FortyGuardCacheError, match="credentials or headers"):
        cache.put({"headers": {"api-key": "must-not-be-stored"}}, sample_result())
