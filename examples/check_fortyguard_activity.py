"""Read one existing FortyGuard activity status without submitting or polling."""

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from thermalshift.config import get_settings
from thermalshift.fortyguard.client import (
    ActivityStatusShapeDiagnostic,
    FortyGuardClient,
    FortyGuardHTTPError,
    FortyGuardResponseError,
)
from thermalshift.fortyguard.models import ActivityStatus

CONFIRMATION_VALUE = "CHECK_EXISTING_FORTYGUARD_ACTIVITY"


class StatusReader(Protocol):
    """One-shot activity status operation used by the inspector."""

    async def get_status(self, activity_id: str) -> ActivityStatus:
        """Return one validated activity status."""
        ...


class StatusShapeReader(Protocol):
    """One-shot sanitized response-shape operation used by shape mode."""

    async def get_status_diagnostic_shape(
        self, activity_id: str
    ) -> ActivityStatusShapeDiagnostic:
        """Return one sanitized activity response-shape summary."""
        ...


async def inspect_activity(
    client: StatusReader,
    activity_id: str,
    *,
    output: Callable[[str], None] = print,
) -> int:
    """Perform exactly one status read and print only allow-listed fields."""
    try:
        status = await client.get_status(activity_id)
    except FortyGuardHTTPError as exc:
        fields = ["status_check=FAILED", "failure_kind=http_error"]
        if exc.status_code is not None:
            fields.append(f"http_status={exc.status_code}")
        output(" ".join(fields))
        return 1
    except FortyGuardResponseError as exc:
        fields = [
            "status_check=FAILED",
            "failure_kind=response_error",
            f"response_reason={exc.reason_code}",
        ]
        if exc.validation_paths:
            paths = ",".join(".".join(path) for path in exc.validation_paths)
            fields.append(f"validation_paths={paths}")
        output(" ".join(fields))
        return 1

    output(f"activity_id={activity_id}")
    output("request_type=GET_STATUS_ONLY")
    output(f"status={status.status}")
    output(f"result_present={'true' if status.result is not None else 'false'}")
    if status.result is not None:
        output(
            "mean_temperature_c="
            f"{status.result.stats_data.temperature_stats.mean}"
        )
    return 0


async def inspect_activity_shape(
    client: StatusShapeReader,
    activity_id: str,
    *,
    output: Callable[[str], None] = print,
) -> int:
    """Perform exactly one raw status read and print sanitized shape metadata."""
    try:
        shape = await client.get_status_diagnostic_shape(activity_id)
    except FortyGuardHTTPError as exc:
        fields = ["status_check=FAILED", "failure_kind=http_error"]
        if exc.status_code is not None:
            fields.append(f"http_status={exc.status_code}")
        output(" ".join(fields))
        return 1
    except FortyGuardResponseError as exc:
        output(
            "status_check=FAILED failure_kind=response_error "
            f"response_reason={exc.reason_code}"
        )
        return 1

    output(f"activity_id={shape.activity_id}")
    output("request_type=GET_STATUS_SHAPE_ONLY")
    match_value = shape.returned_activity_id_matches
    output(
        "returned_activity_id_matches="
        + ("unavailable" if match_value is None else str(match_value).lower())
    )
    output(f"status={shape.status if shape.status is not None else 'unavailable'}")
    output(f"result_present={str(shape.result_present).lower()}")
    output(f"stats_data_present={str(shape.stats_data_present).lower()}")
    output(
        f"temperature_stats_present={str(shape.temperature_stats_present).lower()}"
    )
    for label, value in (
        ("temperature_min_c", shape.temperature_minimum_c),
        ("temperature_max_c", shape.temperature_maximum_c),
        ("temperature_mean_c", shape.temperature_mean_c),
        ("temperature_stddev_c", shape.temperature_standard_deviation_c),
    ):
        output(f"{label}={value if value is not None else 'unavailable'}")
    output(
        "normal_distribution_present="
        f"{str(shape.normal_distribution_present).lower()}"
    )
    _print_axis("normal_x_axis", shape.normal_x_axis, output)
    _print_axis("normal_y_axis", shape.normal_y_axis, output)
    return 0


def _print_axis(label, shape, output) -> None:
    output(f"{label}_present={str(shape.present).lower()}")
    output(f"{label}_length={shape.length if shape.length is not None else 'unavailable'}")
    output(
        f"{label}_types="
        f"number:{shape.number_count},null:{shape.null_count},"
        f"string:{shape.string_count},boolean:{shape.boolean_count},"
        f"object:{shape.object_count},array:{shape.array_count},other:{shape.other_count}"
    )
    output(f"{label}_non_finite_numbers={shape.non_finite_number_count}")


async def run_real_inspection(activity_id: str) -> int:
    """Construct the normal client and perform one GET-only inspection."""
    settings = get_settings()
    api_key = settings.require_fortyguard_api_key()
    async with FortyGuardClient(api_key, base_url=settings.fortyguard_base_url) as client:
        return await inspect_activity(client, activity_id)


async def run_real_shape_inspection(activity_id: str) -> int:
    """Construct the normal client and perform one GET-only shape inspection."""
    settings = get_settings()
    api_key = settings.require_fortyguard_api_key()
    async with FortyGuardClient(api_key, base_url=settings.fortyguard_base_url) as client:
        return await inspect_activity_shape(client, activity_id)


def main(
    argv: Sequence[str] | None = None,
    *,
    inspection_runner: Callable[[str], Awaitable[int]] = run_real_inspection,
    shape_inspection_runner: Callable[[str], Awaitable[int]] = run_real_shape_inspection,
) -> int:
    """Require explicit confirmation before reading an existing activity."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activity-id", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--shape", action="store_true")
    args = parser.parse_args(argv)
    if args.confirm != CONFIRMATION_VALUE:
        print(
            "Status check blocked: pass "
            f"--confirm {CONFIRMATION_VALUE}. No HTTP request was made."
        )
        return 2
    try:
        runner = shape_inspection_runner if args.shape else inspection_runner
        return asyncio.run(runner(args.activity_id))
    except (RuntimeError, ValueError):
        print("status_check=FAILED failure_kind=generic_error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
