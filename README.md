# SkyArch — Passenger intelligence (Flask)

A Python + Flask dashboard for the Kaggle **Airline Passenger Satisfaction** dataset
(129,880 survey responses). Every number, chart and recommendation is computed live
from the CSV files in `data/` with pandas. Nothing on screen is hard-coded.

## Run it

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. The first page load takes about a second while the CSVs are read; after
that the data is cached in memory.

## Project structure

```
skyarch-flask/
├── app.py            # Flask routes: pages, CSV import/reset, CSV exports
├── analytics.py      # Loads the dataset, caches it, computes every metric
├── charts.py         # SVG geometry for the line chart and donut
├── data.py           # Static content only: navigation, page text, architecture, initiative names
├── icons.py          # Inline SVG icons ({{ icon('name') }} in templates)
├── data/
│   ├── train.csv     # 103,904 rows ┐ the active dataset by default
│   ├── test.csv      #  25,976 rows ┘
│   └── uploads/      # CSVs uploaded through the Data workspace (created on first upload)
├── templates/        # Jinja2 HTML: base layout, macros, one template per page
└── static/
    ├── css/style.css
    ├── js/app.js     # Mobile menu, notifications, Ctrl/⌘+K, CSV drag-and-drop
    └── img/          # logo.png, favicon.png
```

## How the numbers are calculated

| Metric | Definition |
|---|---|
| Overall satisfaction | Share of passengers whose `satisfaction` is “satisfied” |
| Avg. service rating | Mean of all 14 service ratings, ignoring 0 (= not applicable) |
| Delayed flights | Departure delay of 15 minutes or more |
| Satisfaction gap | Satisfaction rate of passengers who rate a touchpoint 4–5 minus those who rate it 1–2 |
| Potential lift | (share of passengers rating it 1–2) × satisfaction gap. This is an upper-bound estimate of how much overall satisfaction could rise if those passengers became as satisfied as the 4–5 raters |
| Status | Avg rating ≥ 3.5 Strong · ≥ 3.2 Stable · ≥ 3.0 Watch · below 3.0 At risk |

* **Overview:** cabin-class filter, metrics compared with all classes, satisfaction by age group,
  satisfaction split, highest and lowest rated touchpoints, and the touchpoint with the largest potential lift.
* **Service analytics:** all 14 touchpoints, filterable by travel type or delayed flights.
* **Passenger segments:** business, personal, loyal and delay-affected passengers, each with its top drivers.
* **Improvement roadmap:** the four touchpoints with the largest potential lift become initiatives.
  Ticking one off is remembered in your browser session.

The dataset has no dates, so the dashboard shows satisfaction by age group instead of a monthly trend.

## Updating the data

On **Data workspace**, upload a CSV with the same columns (the “Required columns” list shows them).
Choose **Add to current data** to append it, or **Replace current data** to analyse only that file.
The upload is checked for missing columns, invalid ratings and unexpected satisfaction values. Then every
page is recalculated. **Restore original dataset** switches back to `train.csv` + `test.csv`.
