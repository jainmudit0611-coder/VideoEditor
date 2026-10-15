import statistics
from typing import List, Dict, Any, Optional
from backend.evaluation.schemas import LatencySummary

def calculate_latency_summary(
    timing_records: List[Dict[str, float]]
) -> LatencySummary:
    """
    Computes summary latency metrics (mean, median, min, max, and stage averages)
    across multiple audit execution timing records.
    """
    if not timing_records:
        return LatencySummary(n_samples=0)

    total_durations: List[float] = []
    stage_accumulators: Dict[str, List[float]] = {}

    for record in timing_records:
        if not record:
            continue
        
        # Total duration can be total_worker_duration or sum of stages
        tot = record.get("total_worker_duration") or record.get("total")
        if tot is not None and isinstance(tot, (int, float)):
            total_durations.append(float(tot))

        for k, v in record.items():
            if isinstance(v, (int, float)) and k not in ("total_worker_duration", "total"):
                stage_accumulators.setdefault(k, []).append(float(v))

    n_samples = len(total_durations) if total_durations else len(timing_records)

    mean_tot = round(statistics.mean(total_durations), 3) if total_durations else None
    median_tot = round(statistics.median(total_durations), 3) if total_durations else None
    min_tot = round(min(total_durations), 3) if total_durations else None
    max_tot = round(max(total_durations), 3) if total_durations else None

    stage_means: Dict[str, float] = {}
    for stage, vals in stage_accumulators.items():
        if vals:
            stage_means[stage] = round(statistics.mean(vals), 3)

    return LatencySummary(
        n_samples=n_samples,
        mean_duration_sec=mean_tot,
        median_duration_sec=median_tot,
        min_duration_sec=min_tot,
        max_duration_sec=max_tot,
        stage_latencies=stage_means
    )
