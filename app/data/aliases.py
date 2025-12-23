ALIAS_MAP = {
    "timestamp": ["Timestamp", "timestamp", "time", "epoch", "ts"],
    "flags": ["FLAGS", "flags"],
    "co2": ["CO2", "co2", "co2_ppm"],
    "co2_uncomp": ["CO2_UNCOMP", "co2_uncomp"],
    "pm1_0": ["PM1.0", "PM1", "pm1_0"],
    "pm2_5": ["PM2.5", "PM2_5", "pm2_5"],
    "pm4_0": ["PM4.0", "PM4", "pm4_0"],
    "pm10": ["PM10", "PM10.0", "pm10"],
    "pn0_5": ["PN0.5", "PN0_5", "pn0_5"],
    "pn1_0": ["PN1.0", "PN1", "pn1_0"],
    "pn2_5": ["PN2.5", "PN2_5", "pn2_5"],
    "pn4_0": ["PN4.0", "PN4", "pn4_0"],
    "pn10_0": ["PN10.0", "PN10", "pn10_0"],
    "temp_c": ["TempC", "temp_c", "temperature"],
    "rh": ["RH", "rh", "humidity"],
    "pressure": ["PRESSURE", "pressure", "press"],
    "voc": ["VOC", "voc"],
    "nox": ["NOX", "NOX", "nox"],
}

CANONICAL_ORDER = [
    "timestamp",
    "flags",
    "co2",
    "co2_uncomp",
    "pm1_0",
    "pm2_5",
    "pm4_0",
    "pm10",
    "pn0_5",
    "pn1_0",
    "pn2_5",
    "pn4_0",
    "pn10_0",
    "temp_c",
    "rh",
    "voc",
    "nox",
    "pressure",
]


def normalize_columns(columns: list[str]) -> dict[str, str]:
    normalized = {}
    lower_map = {c.lower(): c for c in columns}
    for canon, aliases in ALIAS_MAP.items():
        for alias in aliases:
            key = alias.lower()
            if key in lower_map:
                normalized[canon] = lower_map[key]
                break
    return normalized
