"""FortyGuard API integration for ThermalShift."""

from thermalshift.fortyguard.client import (
    FortyGuardClient,
    FortyGuardError,
    FortyGuardHTTPError,
    FortyGuardResponseError,
)
from thermalshift.fortyguard.models import ActivityStatus, HeatmapResult
from thermalshift.fortyguard.poller import (
    FortyGuardActivityFailed,
    FortyGuardPollingError,
    FortyGuardPollingTimeout,
    wait_for_completion,
)
from thermalshift.fortyguard.service import create_heatmap

__all__ = [
    "ActivityStatus",
    "FortyGuardActivityFailed",
    "FortyGuardClient",
    "FortyGuardError",
    "FortyGuardHTTPError",
    "FortyGuardPollingError",
    "FortyGuardPollingTimeout",
    "FortyGuardResponseError",
    "HeatmapResult",
    "create_heatmap",
    "wait_for_completion",
]
