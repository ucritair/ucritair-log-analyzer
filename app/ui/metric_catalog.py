from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.data.aliases import CANONICAL_ORDER


@dataclass(frozen=True)
class MetricInfo:
    key: str
    display: str
    axis_label: str
    group: str
    description: str


METRIC_INFO: dict[str, MetricInfo] = {
    "co2": MetricInfo(
        key="co2",
        display="Carbon dioxide (CO2, ppm)",
        axis_label="CO2 (ppm)",
        group="Air",
        description="Carbon dioxide level. Often rises when people are in the room.",
    ),
    "co2_uncomp": MetricInfo(
        key="co2_uncomp",
        display="Carbon dioxide (raw, ppm)",
        axis_label="CO2 raw (ppm)",
        group="Air",
        description="Raw CO2 sensor output before compensation.",
    ),
    "pm1_0": MetricInfo(
        key="pm1_0",
        display="Particles: PM1.0 mass (ug/m3)",
        axis_label="PM1.0 (ug/m3)",
        group="Particles (mass)",
        description="Particle mass concentration for particles up to 1.0 um.",
    ),
    "pm2_5": MetricInfo(
        key="pm2_5",
        display="Particles: PM2.5 mass (ug/m3)",
        axis_label="PM2.5 (ug/m3)",
        group="Particles (mass)",
        description="Fine particle mass concentration (particles up to 2.5 um).",
    ),
    "pm4_0": MetricInfo(
        key="pm4_0",
        display="Particles: PM4.0 mass (ug/m3)",
        axis_label="PM4.0 (ug/m3)",
        group="Particles (mass)",
        description="Particle mass concentration for particles up to 4.0 um.",
    ),
    "pm10": MetricInfo(
        key="pm10",
        display="Particles: PM10 mass (ug/m3)",
        axis_label="PM10 (ug/m3)",
        group="Particles (mass)",
        description="Particle mass concentration for particles up to 10 um.",
    ),
    "pn0_5": MetricInfo(
        key="pn0_5",
        display="Particles: 0.5 um count (sensor units)",
        axis_label="PN0.5 (count)",
        group="Particles (count)",
        description="Particle count for ~0.5 um channel (sensor units).",
    ),
    "pn1_0": MetricInfo(
        key="pn1_0",
        display="Particles: 1.0 um count (sensor units)",
        axis_label="PN1.0 (count)",
        group="Particles (count)",
        description="Particle count for ~1.0 um channel (sensor units).",
    ),
    "pn2_5": MetricInfo(
        key="pn2_5",
        display="Particles: 2.5 um count (sensor units)",
        axis_label="PN2.5 (count)",
        group="Particles (count)",
        description="Particle count for ~2.5 um channel (sensor units).",
    ),
    "pn4_0": MetricInfo(
        key="pn4_0",
        display="Particles: 4.0 um count (sensor units)",
        axis_label="PN4.0 (count)",
        group="Particles (count)",
        description="Particle count for ~4.0 um channel (sensor units).",
    ),
    "pn10_0": MetricInfo(
        key="pn10_0",
        display="Particles: 10 um count (sensor units)",
        axis_label="PN10 (count)",
        group="Particles (count)",
        description="Particle count for ~10 um channel (sensor units).",
    ),
    "temp_c": MetricInfo(
        key="temp_c",
        display="Temperature (C)",
        axis_label="Temp (C)",
        group="Environment",
        description="Air temperature in degrees C.",
    ),
    "rh": MetricInfo(
        key="rh",
        display="Relative humidity (%)",
        axis_label="Humidity (%)",
        group="Environment",
        description="Relative humidity in percent.",
    ),
    "pressure": MetricInfo(
        key="pressure",
        display="Air pressure (hPa)",
        axis_label="Pressure (hPa)",
        group="Environment",
        description="Air pressure in hPa.",
    ),
    "voc": MetricInfo(
        key="voc",
        display="Gas index: VOC (index)",
        axis_label="VOC index",
        group="Gas index",
        description="VOC index (relative scale). 0 means the sensor was off.",
    ),
    "nox": MetricInfo(
        key="nox",
        display="Gas index: NOx (index)",
        axis_label="NOx index",
        group="Gas index",
        description="NOx index (relative scale). 0 means the sensor was off.",
    ),
    "flags": MetricInfo(
        key="flags",
        display="Device status flags",
        axis_label="Flags",
        group="Device",
        description="Device status flags (advanced use).",
    ),
}

GROUP_ORDER = [
    "Air",
    "Particles (mass)",
    "Particles (count)",
    "Environment",
    "Gas index",
    "Device",
    "Other",
]


def metric_display_name(key: str) -> str:
    info = METRIC_INFO.get(key)
    return info.display if info else key


def metric_axis_label(key: str) -> str:
    info = METRIC_INFO.get(key)
    return info.axis_label if info else key


def metric_tooltip(key: str) -> str:
    info = METRIC_INFO.get(key)
    return info.description if info else "Custom column."


def metric_group(key: str) -> str:
    info = METRIC_INFO.get(key)
    return info.group if info else "Other"


def sorted_metric_keys(columns: Iterable[str]) -> list[str]:
    columns_set = set(columns)
    ordered = [key for key in CANONICAL_ORDER if key in columns_set]
    extras = sorted([key for key in columns_set if key not in ordered])
    return ordered + extras
