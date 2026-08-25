"""Export safe public simulation grids from complete local cache; never uses HTTP."""

import argparse
from pathlib import Path

from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.web.thermal_grid import export_thermal_grid, write_thermal_grid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window",
        required=True,
        choices=("summer-midday-v1", "winter-overnight-v1"),
    )
    parser.add_argument("--evidence-root", type=Path, default=Path("evidence"))
    args = parser.parse_args(argv)
    artifact = export_thermal_grid(args.window, HeatmapResultCache())
    path = args.evidence_root / args.window / "thermal_grid.json"
    write_thermal_grid(artifact, path)
    print(f"Wrote sanitized {len(artifact['entries'])}-entry grid to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
