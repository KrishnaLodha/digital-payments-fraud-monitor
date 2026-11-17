# Submission verification — 5 November 2026

## Current deliverable

`Payment Fraud Monitor - Final.twbx` is the actual submission file in this folder. It contains the embedded 100,000-row sample, a Hyper extract for auxiliary tables, and imported custom geocoding. The old file is retained under `archive`.

## Implemented requirements

| Requirement | Result |
|---|---|
| Operations dashboard | Six KPIs, separate hourly count/rate charts, threshold-driven alert chart and approval proxy |
| Genuine/fraud heatmaps | Two weekday × hour grids, Monday first |
| Customer LOD outliers | FIXED mean/std dev, deviation score, parameter-driven classification and eligible-record filter |
| Rolling device analysis | Tableau WINDOW_SUM over a 31-day zero-filled scaffold, partitioned by device |
| Threshold simulator | Parameter-linked KPIs plus 101-cutoff trade-off curves |
| Geospatial/custom geocoding | Imported Payment City role; generated map coordinates; ten city marks and five unmapped fraud cases |
| Investigator drill-down | Full-population detail table, source actions, full case fields in tooltips; separate alert review queue |
| Story | Four Story points, captions checked, cutoff 70 and 76 captured states |
| Stretch deliverables | Shared-device accounts view and daily investigator PDF |

## Numeric checks

The source CSV was independently recalculated and compared with the included scenario table. Tableau crosstabs were then copied from the actual KPI worksheets in isolated QA copies with changed parameter values. Those copies were opened one at a time.

| Cutoff | Alerts | Captured fraud | False positives | Missed fraud | Net saving USD |
|---:|---:|---:|---:|---:|---:|
| 0 | 100,000 | 129 / 100.0% | 99,871 | 0 | −3,845,598.50 |
| 70 | 347 | 103 / 79.8% | 244 | 26 | 132,952.57 |
| 76 | 198 | 97 / 75.2% | 101 | 32 | 138,196.29 |
| 100 | 26 | 26 / 20.2% | 0 | 103 | 50,086.66 |

All 93 Tableau rolling-device values (three devices × 31 days) were exported as a crosstab and exactly matched independent timestamp-based trailing-seven-day calculations. Values can decline when payments leave the window.

The LOD baseline check found exactly **two eligible sample-local records**. Both are classified outside the baseline at cutoff 0.5 and inside it at cutoff 1. The Python baseline fields cover 300 records; this is explicitly distinguished from sample-local Tableau LOD eligibility.

The four Story captions and captured threshold states were inspected. Cutoff 76 maximizes the 101-row net-saving scenario table under the stated assumptions.

## Application and package checks

- Tableau workbook schema validation passed after the final XML changes.
- The packaged ZIP integrity check passed.
- Tableau Desktop reopened the saved submission package.
- Query batches for the dashboards reported no query/batch errors.
- Imported `Local Data/Payment_City.tds` and `Local Data/GeocodingData.hyper` are present in the saved package; this is an actual Tableau custom-geocoding import, not just a coordinate CSV.
- Exported dashboard images were reviewed without capturing the user's desktop.
- The investigator table uses Fit Width and scrolls; it does not compress the full population into one image.
- Selecting the Delhi map mark triggered the investigator query and returned **19,301** records, exactly matching the source-city count.
- Heatmap, outlier and device action definitions were checked for source/target fields and existing worksheets. Their individual mouse-selection paths were not all exercised end to end; the Delhi action is the directly observed click-through test.
- Relevant analytic tabs are visible; individual KPI helpers remain hidden inside the workbook.

## Submission limitations to explain

This is a static synthetic, stratified sample. The risk score and geographic/device enrichment are illustrative. Sample-local customer histories are too sparse for broad anomaly conclusions. Approval is a not-flagged proxy. USD savings use the explicit teaching conversion of one PaySim amount unit to $0.001, and are not measured bank savings. The full 6.36-million-row migration is documented as future deployment work.
