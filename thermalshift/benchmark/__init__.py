"""Reproducible evaluation tools for ThermalShift schedulers."""

from .comparison import PairwiseComparison, compare_metrics, format_headline
from .models import BenchmarkMetrics, BenchmarkReport, BenchmarkRun, BenchmarkScenario
from .runner import run_benchmark
from .synthetic import create_synthetic_scenario

__all__ = [
    "BenchmarkMetrics",
    "BenchmarkReport",
    "BenchmarkRun",
    "BenchmarkScenario",
    "PairwiseComparison",
    "compare_metrics",
    "create_synthetic_scenario",
    "format_headline",
    "run_benchmark",
]
