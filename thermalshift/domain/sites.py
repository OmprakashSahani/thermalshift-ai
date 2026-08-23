"""Deterministic registry of synthetic sites for controlled benchmarks."""

from thermalshift.domain.models import Site


def get_default_sites() -> tuple[Site, ...]:
    """Return four modeled U.S. sites in stable benchmark order.

    Every 64-GPU capacity is a synthetic benchmark parameter, not a statement
    about any real facility.
    """
    return (
        Site(
            site_id="ashburn-va",
            name="Modeled Ashburn Compute Site",
            latitude=39.0437,
            longitude=-77.4875,
            timezone="America/New_York",
            total_gpu_capacity=64,
        ),
        Site(
            site_id="phoenix-az",
            name="Modeled Phoenix Compute Site",
            latitude=33.4484,
            longitude=-112.0740,
            timezone="America/Phoenix",
            total_gpu_capacity=64,
        ),
        Site(
            site_id="san-antonio-tx",
            name="Modeled San Antonio Compute Site",
            latitude=29.4241,
            longitude=-98.4936,
            timezone="America/Chicago",
            total_gpu_capacity=64,
        ),
        Site(
            site_id="atlanta-ga",
            name="Modeled Atlanta Compute Site",
            latitude=33.7490,
            longitude=-84.3880,
            timezone="America/New_York",
            total_gpu_capacity=64,
        ),
    )
