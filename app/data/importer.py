from __future__ import annotations

from pathlib import Path
import pandas as pd

from app.core.config import ProcessingConfig
from app.data.aliases import normalize_columns, CANONICAL_ORDER
from app.data.dataset import Dataset
from app.data.gaps import detect_gaps
from app.data.mask_rules import apply_validity_masks
from app.diagnostics.flatline import FlatlineConfig, flag_flatlines


class DatasetImporter:
    def load_csv(self, path: Path, config: ProcessingConfig) -> Dataset:
        delimiter = config.delimiter or self._detect_delimiter(path)
        df = pd.read_csv(path, sep=delimiter, encoding="utf-8", engine="python")
        df.columns = [c.strip() for c in df.columns]

        rename_map = {}
        normalized = normalize_columns(list(df.columns))
        for canon, original in normalized.items():
            rename_map[original] = canon
        df = df.rename(columns=rename_map)

        if "timestamp" not in df.columns:
            raise ValueError("CSV missing timestamp column")

        df = self._coerce_numeric(df)
        df = self._convert_timestamp(df)
        df = self._sort_dedup(df, config)

        mask_result = apply_validity_masks(df, config)
        clean = mask_result.clean
        masks = mask_result.masks

        resampled = None
        if config.resample_interval:
            resampled = self._resample(clean, config.resample_interval)

        gaps = detect_gaps(clean["timestamp"], config.gap_factor)
        flags = {}
        if config.flatline_diag_enabled:
            flat_cfg = FlatlineConfig()
            flat_df = clean.set_index("timestamp")
            flags = flag_flatlines(flat_df, flat_cfg)
            if config.flatline_automask:
                for col, mask in flags.items():
                    if col.startswith("pm") or col.startswith("pn"):
                        clean.loc[mask.values, col] = pd.NA
                        if col in masks:
                            masks[col] = masks[col] & ~mask.values

        metadata = {
            "path": str(path),
            "delimiter": delimiter,
            "gaps": gaps,
            "mask_reasons": mask_result.reasons,
            "columns": [c for c in CANONICAL_ORDER if c in df.columns],
            "resample_interval": config.resample_interval,
            "resampled_rows": int(resampled.shape[0]) if resampled is not None else None,
        }

        return Dataset(
            name=path.stem,
            raw=df,
            clean=clean,
            masks=masks,
            flags=flags,
            metadata=metadata,
            resampled=resampled,
        )

    def _detect_delimiter(self, path: Path) -> str:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            first_line = handle.readline()
        comma = first_line.count(",")
        semicolon = first_line.count(";")
        return "," if comma >= semicolon else ";"

    def _coerce_numeric(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            if col == "timestamp":
                continue
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def _convert_timestamp(self, df: pd.DataFrame) -> pd.DataFrame:
        ts = pd.to_numeric(df["timestamp"], errors="coerce")
        if ts.dropna().empty:
            raise ValueError("Timestamp column is not numeric")

        median = ts.dropna().median()
        if median > 1e12:
            unit = "ms"
        else:
            unit = "s"
        df["timestamp"] = pd.to_datetime(ts, unit=unit, utc=True)
        return df

    def _sort_dedup(self, df: pd.DataFrame, config: ProcessingConfig) -> pd.DataFrame:
        df = df.sort_values("timestamp")
        df = df.drop_duplicates(subset=["timestamp"], keep=config.dedup_keep)
        df = df.reset_index(drop=True)
        return df

    def _resample(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        indexed = df.set_index("timestamp")
        numeric_cols = indexed.select_dtypes(include=["number"]).columns.tolist()
        if "flags" in indexed.columns and "flags" not in numeric_cols:
            numeric_cols.append("flags")

        resampled = indexed[numeric_cols].resample(interval).mean()
        if "flags" in indexed.columns:
            flags = indexed["flags"].resample(interval).ffill()
            resampled["flags"] = flags
        resampled = resampled.reset_index()
        return resampled
