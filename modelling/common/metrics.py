"""Shared forecasting / classification metrics with safe edge-case handling.

Kept dependency-light (numpy only) so every module can import it without pulling
heavy ML libraries.
"""
from __future__ import annotations

import numpy as np


def _align(y_true, y_pred) -> tuple[np.ndarray, np.ndarray]:
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: {y_true.shape} vs {y_pred.shape}")
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    return y_true[mask], y_pred[mask]


def rmse(y_true, y_pred) -> float:
    yt, yp = _align(y_true, y_pred)
    if yt.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean((yt - yp) ** 2)))


def mae(y_true, y_pred) -> float:
    yt, yp = _align(y_true, y_pred)
    if yt.size == 0:
        return float("nan")
    return float(np.mean(np.abs(yt - yp)))


def mape(y_true, y_pred) -> float:
    """Mean absolute percentage error (%), ignoring points where y_true == 0."""
    yt, yp = _align(y_true, y_pred)
    nz = yt != 0
    if not nz.any():
        return float("nan")
    return float(np.mean(np.abs((yt[nz] - yp[nz]) / yt[nz])) * 100.0)


def directional_accuracy(y_true, y_pred) -> float:
    """Fraction of steps where predicted direction of change matches actual (%).

    Especially relevant for stock prices, where getting the *direction* right
    matters more than the absolute level.
    """
    yt, yp = _align(y_true, y_pred)
    if yt.size < 2:
        return float("nan")
    return float(np.mean(np.sign(np.diff(yt)) == np.sign(np.diff(yp))) * 100.0)


def regression_report(y_true, y_pred) -> dict[str, float]:
    return {
        "RMSE": rmse(y_true, y_pred),
        "MAE": mae(y_true, y_pred),
        "MAPE": mape(y_true, y_pred),
        "DirectionalAccuracy": directional_accuracy(y_true, y_pred),
    }
