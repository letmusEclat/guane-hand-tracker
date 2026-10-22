"""Funciones geometricas y estado estable para reconocer una pinza."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Protocol, Sequence


class Point(Protocol):
    x: float
    y: float


WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_TIP = 8
MIDDLE_MCP = 9
PINKY_MCP = 17


def distance(a: Point, b: Point) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def palm_scale(landmarks: Sequence[Point]) -> float:
    """Tamano robusto de la palma en coordenadas normalizadas."""
    if len(landmarks) < 21:
        raise ValueError("Se esperaban 21 puntos de la mano")
    width = distance(landmarks[INDEX_MCP], landmarks[PINKY_MCP])
    length = distance(landmarks[WRIST], landmarks[MIDDLE_MCP])
    return max(width, length, 1e-6)


def pinch_ratio(landmarks: Sequence[Point]) -> float:
    """Distancia pulgar-indice dividida por el tamano de la palma."""
    return distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / palm_scale(landmarks)


def pinch_strength(ratio: float, minimum: float = 0.16, maximum: float = 0.80) -> float:
    """Convierte la distancia normalizada en intensidad de 0 (abierta) a 1."""
    if maximum <= minimum:
        raise ValueError("maximum debe ser mayor que minimum")
    return 1.0 - min(1.0, max(0.0, (ratio - minimum) / (maximum - minimum)))


@dataclass
class PinchTracker:
    """Suavizado exponencial e histeresis para evitar parpadeos de estado."""

    close_threshold: float = 0.38
    open_threshold: float = 0.50
    smoothing: float = 0.35
    active: bool = False
    smoothed_ratio: float | None = None

    def __post_init__(self) -> None:
        if self.close_threshold >= self.open_threshold:
            raise ValueError("close_threshold debe ser menor que open_threshold")
        if not 0.0 < self.smoothing <= 1.0:
            raise ValueError("smoothing debe estar entre 0 (exclusivo) y 1")

    def update(self, ratio: float) -> tuple[bool, float, float]:
        if self.smoothed_ratio is None:
            self.smoothed_ratio = ratio
        else:
            self.smoothed_ratio += self.smoothing * (ratio - self.smoothed_ratio)

        if self.active and self.smoothed_ratio >= self.open_threshold:
            self.active = False
        elif not self.active and self.smoothed_ratio <= self.close_threshold:
            self.active = True

        return self.active, pinch_strength(self.smoothed_ratio), self.smoothed_ratio

    def reset(self) -> None:
        self.active = False
        self.smoothed_ratio = None

