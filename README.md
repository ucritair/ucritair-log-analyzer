# μCritAir Log Analyzer

Desktop app for importing μCritAir/ucritter CSV logs, cleaning data, plotting metrics, and running AQI/ventilation/exposure analyses.

## Highlights
- CSV import with alias mapping, dedup, gap detection, and per-metric validity masks.
- PM/PN zeros are treated as valid measurements by default.
- VOC/NOx zeros are masked as inactive by default (toggleable).
- Interactive plotting with filters, raw+filtered overlays, time-range selection, and multi-axis support.
- Analyses: AQI (PM-only packs), CO2 ACH, PN10 eACH, and exposure/dosimetry.
- Project save/load and exports for clean/filtered/AQI/analysis results.

## Run

```bash
python -m app.main
```

## Notes
- Internal time is UTC; display supports UTC or local time.
- Flatline detection is diagnostic only unless you enable auto-masking in settings.
