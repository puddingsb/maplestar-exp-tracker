from __future__ import annotations

import time
from dataclasses import dataclass


DEFAULT_RATE_WINDOWS_SECONDS = (60, 300, 600, 1800)


@dataclass
class RateSnapshot:
    window_seconds: int
    rate_per_min: float | None = None
    sample_count: int = 0
    span_seconds: float = 0.0
    saturated: bool = False


class RateView:
    """Read-only rate calculations over accepted EXP samples."""

    def __init__(
        self,
        samples,
        total_getter,
        *,
        windows=DEFAULT_RATE_WINDOWS_SECONDS,
        min_delta_tolerance=50_000,
        outlier_min_positive_segments=5,
        outlier_multiplier=4.0,
        outlier_mad_multiplier=8.0,
    ):
        self.samples = samples
        self.total_getter = total_getter
        self.windows = tuple(windows)
        self.min_delta_tolerance = min_delta_tolerance
        self.outlier_min_positive_segments = outlier_min_positive_segments
        self.outlier_multiplier = outlier_multiplier
        self.outlier_mad_multiplier = outlier_mad_multiplier

    def _window_samples(self, window_s, now=None):
        if len(self.samples) < 2:
            return []
        now = now if now is not None else time.time()
        cutoff = now - window_s
        window_samples = []
        previous = None
        for sample in self.samples:
            if sample[0] < cutoff:
                previous = sample
                continue
            if previous is not None and not window_samples:
                window_samples.append(previous)
            window_samples.append(sample)
        return window_samples

    def rate_per_min(self, window_s, now=None, min_span=20):
        window_samples = self._window_samples(window_s, now=now)
        if len(window_samples) < 2:
            return None
        span = window_samples[-1][0] - window_samples[0][0]
        if span < min_span:
            return None

        segments = []
        for previous, current in zip(window_samples, window_samples[1:]):
            dt = current[0] - previous[0]
            gained = current[1] - previous[1]
            if dt <= 0 or gained < 0:
                continue
            segments.append((dt, gained, gained / (dt / 60)))
        if not segments:
            return 0

        filtered = segments
        positive_rates = sorted(rate for _dt, gained, rate in segments if gained > 0)
        if len(positive_rates) >= self.outlier_min_positive_segments:
            mid = len(positive_rates) // 2
            if len(positive_rates) % 2:
                median_rate = positive_rates[mid]
            else:
                median_rate = (positive_rates[mid - 1] + positive_rates[mid]) / 2
            deviations = sorted(abs(rate - median_rate) for rate in positive_rates)
            dev_mid = len(deviations) // 2
            if len(deviations) % 2:
                mad = deviations[dev_mid]
            else:
                mad = (deviations[dev_mid - 1] + deviations[dev_mid]) / 2
            outlier_limit = max(
                median_rate * self.outlier_multiplier,
                median_rate + max(mad * self.outlier_mad_multiplier, self.min_delta_tolerance * 60),
            )
            filtered = [
                (dt, gained, rate)
                for dt, gained, rate in segments
                if gained == 0 or rate <= outlier_limit
            ]

        trusted_gained = sum(gained for _dt, gained, _rate in filtered)
        return trusted_gained / (span / 60)

    def snapshot(self, now=None):
        now = now if now is not None else time.time()
        result = {}
        for window_s in self.windows:
            window_samples = self._window_samples(window_s, now=now)
            snap = RateSnapshot(window_seconds=window_s)
            if len(window_samples) >= 2:
                span = window_samples[-1][0] - window_samples[0][0]
                snap.span_seconds = max(0.0, span)
                snap.sample_count = len(window_samples)
                snap.saturated = span >= window_s * 0.85
                snap.rate_per_min = self.rate_per_min(window_s, now=now)
            result[window_s] = snap
        return result

    def session_average(self, session_start, now=None):
        if session_start is None or not self.samples:
            return None
        now = now if now is not None else time.time()
        elapsed = now - session_start
        if elapsed <= 0:
            return None
        total = self.total_getter()
        return total / (elapsed / 60) if total > 0 else 0.0

    def interval_accumulated(self, window_s, now=None):
        window_samples = self._window_samples(window_s, now=now)
        if len(window_samples) < 2:
            return None
        gained = window_samples[-1][1] - window_samples[0][1]
        return max(0, int(gained))
