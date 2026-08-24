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
    response_reason: str | None = None
    validation_paths: tuple[tuple[str, ...], ...] = ()

    def output_fields(self) -> str:
        """Format only allow-listed structured values."""
        fields = [f"failure_kind={self.failure_kind}"]
        if self.activity_id is not None:
            fields.append(f"activity_id={self.activity_id}")
        if self.http_status is not None:
            fields.append(f"http_status={self.http_status}")
        if self.response_reason is not None:
            fields.append(f"response_reason={self.response_reason}")
        if self.validation_paths:
            rendered_paths = ",".join(".".join(path) for path in self.validation_paths)
            fields.append(f"validation_paths={rendered_paths}")
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
            error.response_reason,
            error.validation_paths,
        )
    if isinstance(error, FortyGuardHTTPError):
        return SafeFailureDiagnostic("http_error", http_status=error.status_code)
    if isinstance(error, FortyGuardResponseError):
        return SafeFailureDiagnostic(
            "response_error",
            response_reason=error.reason_code,
            validation_paths=error.validation_paths,
        )
    return SafeFailureDiagnostic("generic_error")
