from dataclasses import dataclass

import pytest

from sensor.pinch import PinchTracker, palm_scale, pinch_ratio, pinch_strength


@dataclass
class Point:
    x: float = 0.0
    y: float = 0.0


def hand(thumb=(0.1, 0.0), index=(0.2, 0.0)) -> list[Point]:
    points = [Point() for _ in range(21)]
    points[0] = Point(0.0, 0.0)
    points[4] = Point(*thumb)
    points[5] = Point(-0.5, 1.0)
    points[8] = Point(*index)
    points[9] = Point(0.0, 1.0)
    points[17] = Point(0.5, 1.0)
    return points


def test_ratio_is_normalized_by_palm_size() -> None:
    landmarks = hand(thumb=(0.0, 0.0), index=(0.25, 0.0))
    assert palm_scale(landmarks) == pytest.approx(1.0)
    assert pinch_ratio(landmarks) == pytest.approx(0.25)


def test_strength_is_clamped() -> None:
    assert pinch_strength(0.0) == 1.0
    assert pinch_strength(1.5) == 0.0


def test_tracker_uses_hysteresis() -> None:
    tracker = PinchTracker(smoothing=1.0)
    assert tracker.update(0.30)[0] is True
    assert tracker.update(0.45)[0] is True
    assert tracker.update(0.55)[0] is False


def test_invalid_landmark_count() -> None:
    with pytest.raises(ValueError):
        palm_scale([Point()] * 3)


def test_tracker_reset_clears_previous_pinch() -> None:
    tracker = PinchTracker(smoothing=1.0)
    tracker.update(0.2)
    tracker.reset()
    assert tracker.active is False
    assert tracker.smoothed_ratio is None


@pytest.mark.parametrize("smoothing", [0.0, -0.1, 1.1])
def test_tracker_rejects_invalid_smoothing(smoothing: float) -> None:
    with pytest.raises(ValueError):
        PinchTracker(smoothing=smoothing)


def test_tracker_rejects_overlapping_thresholds() -> None:
    with pytest.raises(ValueError):
        PinchTracker(close_threshold=0.5, open_threshold=0.5)

