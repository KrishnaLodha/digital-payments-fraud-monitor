# Digital Payments and UPI Transaction Fraud Monitoring

## Problem and solution

Payment risk teams need to see transaction health, find unusual activity, and decide which risk scores should trigger review. This Tableau project uses an enriched, synthetic PaySim sample to demonstrate that workflow. The packaged workbook contains three dashboards (two at 1200 × 800 and Fraud Pattern Explorer at 1200 × 1400), a four-point Story, the 100,000-row CSV, a threshold scenario table, shared-device links, and a city coordinate reference.

## Data and scope

- **100,000 sampled payments**, of which **129 are labelled fraud**. The sample fraud rate is **0.129% = 12.9 basis points (bps)**. Because the data is synthetic and stratified, this is a sample statistic, not a production UPI fraud rate.
- The sample spans January 2026. Added fields include timestamp, hour, weekday, city, coordinates, device ID, customer baseline, deviation score, and a synthetic 0–100 risk score.
- **Value at risk:** 152,466,502 PaySim amount units. **Average ticket:** 181,811 amount units. The source does not identify these as USD or INR.
- The risk cutoff starts at **70**. A transaction is flagged when `risk_score >= Risk Threshold`.

## Dashboard 1 — Live Payment Health

The operations overview shows transaction count, average transactions per observed hour, approval **proxy**, fraud rate in bps, value at risk, and average ticket. The approval proxy is the share **not flagged** at the selected cutoff; it is not a bank authorization rate. The fraud and volume hourly trends use separate charts and scales so a low-volume hour cannot be mistaken for a high-volume incident. The transaction-type chart shows where review alerts arise, using a restrained single color. The risk slider is also available here.

**Interpretation:** At 05:00 there are 10 fraud cases among only 32 payments, producing a 31.3% hourly fraud rate. At 19:00 there are about 10,240 payments and four fraud cases. Always read the rate with its denominator; the early-morning spike is striking but based on a small count.

## Dashboard 2 — Fraud Pattern Explorer

The India-centred city map uses circle size for transaction volume and color for fraud rate. Five labelled fraud records have unrecognized location and cannot be plotted as city coordinates. Two weekday-by-hour heat maps compare genuine payment density with confirmed-fraud density. Weekdays are ordered Monday through Sunday. The customer chart uses Tableau FIXED LOD expressions to calculate the mean and sample standard deviation of amount for each originating account. Only **two records** in this stratified sample have a usable sample-local standard deviation. Their deviation scores are about −0.707 and +0.707; changing **Std Dev Cutoff** from 0.5 to 1 switches both from outlier to within-baseline. This is a demonstration of the method, not evidence of a broad customer anomaly pattern. The device chart shows three sampled devices over all 31 January days. A zero-filled daily scaffold supports the Tableau table calculation `WINDOW_SUM(SUM([transaction_count]), -6, 0)`, addressed by January day and partitioned by device. All 93 displayed counts were exported from Tableau and matched independent calculations. The **Investigator Detail** table can inspect every payment, with readable case ID, time, type, city, device, amount and risk; origin/destination account names, balances, full transaction ID, deviation and fraud label are available on hover. Chart actions select matching cases; the separate **Alert Review Queue** retains the threshold-aware review list.

**Interpretation:** Confirmed fraud is concentrated in `TRANSFER` (63 cases) and `CASH_OUT` (66 cases). Delhi has 49 cases and Kolkata 41. Case counts do not establish that those cities have the highest *rates*; the map provides the corresponding transaction-volume context. The supplied Python baseline columns cover 300 sampled rows, while recomputing baselines from the sample itself with Tableau LOD leaves just two eligible rows. These are different populations and must not be presented as equivalent. The shared-device count is an illustration of linked accounts, not a measured fraud rate.

Custom geocoding was imported in Tableau Desktop from a ten-city `Payment City, Latitude, Longitude` reference. The map City field uses the custom role `[Payment_City].[Payment City]` and Tableau generated map coordinates. The saved TWBX includes `Local Data/Payment_City.tds` and `Local Data/GeocodingData.hyper`, so this requirement is demonstrable and portable. Unknown locations are deliberately left unmapped rather than assigned fabricated coordinates.

## Dashboard 3 — Threshold & Cost Simulator

Move the **Risk Threshold** slider to update alerts, captured-fraud share, false positives, missed fraud, captured fraud value, and net saving. The scenario includes separate operating-cost components and three separately scaled curves across all integer cutoffs from 0 through 100: captured value, false positives, and net saving. These curves use an included 101-row scaffold rather than a single parameter point.

The source amount has no verified currency. For this teaching scenario only, **1 PaySim amount unit = $0.001**. The model assumes full captured fraud amount is preventable and uses **$25 per alert**, **$15 per false positive**, and **$500 per missed case**. Net saving is converted captured value minus review and false-positive costs. The missed-case penalty is shown in estimated operating cost, not subtracted again from net saving. All USD figures are model outputs, not booked losses.

| Risk cutoff | Alerts | Fraud captured | False positives | Missed fraud | Net saving |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 70 | 347 | 103 | 244 | 26 | $132,953 |
| **76** | **198** | **97** | **101** | **32** | **$138,196** |

Under these explicit assumptions, **76 maximizes net saving among cutoffs 0–100**. Relative to 70, it reduces review alerts by 149 and false positives by 143, while missing six additional labelled fraud cases. The recommendation is sensitive to the assumed conversion and costs; it is a scenario choice, not a calibrated production policy.

## Story and extra views

The four Story points cover the problem, where/when/how fraud appears, the cutoff-70 trade-off, and the cutoff-76 recommendation. The separate **Shared Device Accounts** worksheet shows the 30 most active linked devices from the packaged entity-link file. The **Geocoding Reference** worksheet displays the packaged coordinate lookup. **Investigator Detail** supports inspection. A separate, one-page **Investigator Daily Report.pdf** gives a reproducible sample snapshot for January 13, 2026 at cutoff 76; it was generated from the packaged CSV and is not a Tableau dashboard export.

## Methods and calculated fields

- Fraud bps: `10000 × SUM(isFraud) / COUNT(transaction_id)`.
- Average transactions per observed hour: `COUNT(transaction_id) / COUNTD(DATETRUNC('hour', timestamp))`.
- Approval proxy: `1 − SUM(Flagged by Threshold) / COUNT(transaction_id)`.
- Customer baseline mean: `{ FIXED [nameOrig] : AVG([amount]) }`; standard deviation: `{ FIXED [nameOrig] : STDEV([amount]) }`. Deviation is `(amount − mean) / std dev`; missing/zero standard deviations are excluded. The parameter-controlled outlier chart shows the two eligible sample-local records.
- The device table calculation uses a daily scaffold rebuilt from the actual timestamp dates, including zero days. Its addressing is explicitly day; each device is a separate partition. The curve can fall when older payments leave the seven-day window.
- Captured fraud value sums amounts where `isFraud = 1` and the risk score meets the selected cutoff.

## Reproducibility and handoff

Open `Payment Fraud Monitor - Final.twbx` in Tableau Desktop. A `.twbx` is a Tableau workbook package containing its data and supporting files. Keep this local file even if a Tableau Cloud trial expires. The source CSV and scenario/reference CSVs are inside the package; they do not need to be shared separately for the 100,000-row version.

The full 6.36-million-row dataset is **not** in this package. To use it, make a separate workbook copy, point the source to the full prepared file, create a Tableau `.hyper` extract, and refresh it. Recheck all totals, the 0–100 threshold curve and recommendation, customer-history coverage, device-window interpretation, map nulls, dashboard actions, and Story captions. A stratified-sample recommendation should not be transferred to the full population without recalculation.

## Validation and limits

The packaged workbook passed the Tableau 2026.2 workbook schema validator and ZIP integrity check. Tableau Desktop opened the final package. Application query batches for all three dashboards reported no query or batch errors. The threshold scaffold returned 101 rows, the map 10 city marks, the heatmaps 157 populated cells, and the alert review queue 373 rows at cutoff 70 (the dashboard investigator can inspect the full sample). Exported dashboard images were inspected without desktop screenshots. The investigator table uses Fit Width to keep rows readable and scrollable. Action definitions map city, weekday/hour, transaction ID and device ID into the detail view; live click-through testing is tracked separately in VALIDATION_REPORT.md.

## 5 November repair

The previous final workbook had blank threshold curves and several other empty views. This repair packages the supplemental data in a Tableau Hyper extract, corrects invalid references, restores the investigator transaction list, removes filter actions that had no source dimension, improves number labels, and centres the map on India. The previous final package is saved in `work/Payment Fraud Monitor - Previous Final Backup.twbx`.


## Submission contents and presentation

The current package contains **31 worksheets, three dashboards and one four-point Tableau Story**. Relevant analysis worksheets are visible for inspection; individual KPI helpers remain inside the workbook but are hidden from navigation. `Alert Review Queue` provides the 373 review/known-fraud cases at cutoff 70; `Investigator Detail` supports the full population so genuine payment selections can also be investigated. `Shared Device Accounts` is the stretch entity view, sourced from the supplied synthetic entity-link table.

Start a professor demonstration with Live Payment Health, explain bps and the denominator behind the 05:00 spike, then show the simulator at 70 and explain why the scenario optimum is 76. On Explorer, compare genuine and fraud heatmaps, explain that locations and device links are synthetic, demonstrate the Std Dev Cutoff, and inspect a case. Finish with the Story recommendation and limitations. Do not describe the sample as a live UPI feed or the scenario savings as measured bank savings.

### What this project teaches

- Rates and counts must be read together; a low-volume hour can have a high rate.
- Threshold choice trades review workload and false positives against missed fraud.
- Scenario economics depend on explicit cost and amount-conversion assumptions.
- FIXED LOD calculations group by customer; sparse samples can make a standard deviation unavailable.
- A rolling window needs complete calendar days and explicit addressing/partitioning.
- Geographic case counts differ from rates, and unmapped records must remain visible.
- Linked-device activity is an investigation clue, not proof of fraud.
- A packaged workbook preserves data and custom geocoding locally after a Cloud trial ends.

### Important data limitations

The sample is synthetic and stratified. Most account IDs occur once, device histories are sparse, and coordinates/device reuse were added for illustration. A two-point LOD demonstration should not be sold as a validated anomaly detector. There is no bank authorization outcome field, so approval is explicitly a not-flagged proxy. Full-dataset migration and recalibration remain a future deployment task rather than part of the sample submission.

Custom geocoding format and packaging follow Tableau's official documentation: https://help.tableau.com/current/pro/desktop/en-us/custom_geocoding.htm and https://help.tableau.com/current/pro/desktop/en-us/maps_customgeocode_datablend.htm.
