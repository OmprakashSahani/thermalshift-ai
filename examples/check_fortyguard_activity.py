"""Read one existing FortyGuard activity status without submitting or polling."""

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from thermalshift.config import get_settings
from thermalshift.fortyguard.client import (
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


async def run_real_inspection(activity_id: str) -> int:
    """Construct the normal client and perform one GET-only inspection."""
    settings = get_settings()
    api_key = settings.require_fortyguard_api_key()
    async with FortyGuardClient(api_key, base_url=settings.fortyguard_base_url) as client:
        return await inspect_activity(client, activity_id)


def main(
    argv: Sequence[str] | None = None,
    *,
    inspection_runner: Callable[[str], Awaitable[int]] = run_real_inspection,
) -> int:
    """Require explicit confirmation before reading an existing activity."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activity-id", required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args(argv)
    if args.confirm != CONFIRMATION_VALUE:
        print(
            "Status check blocked: pass "
            f"--confirm {CONFIRMATION_VALUE}. No HTTP request was made."
        )
        return 2
    try:
        return asyncio.run(inspection_runner(args.activity_id))
    except (RuntimeError, ValueError):
        print("status_check=FAILED failure_kind=generic_error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
