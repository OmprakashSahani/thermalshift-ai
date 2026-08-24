"""Credential-safe structured diagnostics for collector failures."""

from dataclasses import dataclass
from typing import Literal

from thermalshift.fortyguard.client import FortyGuardHTTPError, FortyGuardResponseError
from thermalshift.fortyguard.poller import (
    FortyGuardActivityFailed,
    FortyGuardPollingTimeout,
)
from thermalshift.fortyguard.service import FortyGuardStatusRequestError

FailureKind = Literal[
    "terminal_activity_failed",
    "polling_timeout",
    "http_error",
    "response_error",
    "generic_error",
]


@dataclass(frozen=True, slots=True)
class SafeFailureDiagnostic:
    """Fields approved for collector failure output."""

    failure_kind: FailureKind
    activity_id: str | None = None
    http_status: int | None = None

    def output_fields(self) -> str:
        """Format only allow-listed structured values."""
        fields = [f"failure_kind={self.failure_kind}"]
        if self.activity_id is not None:
            fields.append(f"activity_id={self.activity_id}")
        if self.http_status is not None:
            fields.append(f"http_status={self.http_status}")
        return " ".join(fields)


def diagnose_failure(error: RuntimeError | ValueError) -> SafeFailureDiagnostic:
    """Classify a handled failure without exposing its exception message."""
    if isinstance(error, FortyGuardActivityFailed):
        return SafeFailureDiagnostic("terminal_activity_failed", error.activity_id)
    if isinstance(error, FortyGuardPollingTimeout):
        return SafeFailureDiagnostic("polling_timeout", error.activity_id)
    if isinstance(error, FortyGuardStatusRequestError):
        return SafeFailureDiagnostic(
            error.failure_kind,
            error.activity_id,
            error.status_code,
        )
    if isinstance(error, FortyGuardHTTPError):
        return SafeFailureDiagnostic("http_error", http_status=error.status_code)
    if isinstance(error, FortyGuardResponseError):
        return SafeFailureDiagnostic("response_error")
    return SafeFailureDiagnostic("generic_error")
