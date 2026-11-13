# NYC Property Market Dashboard

An interactive dashboard that looks at how neighborhood factors relate to residential property prices across New York City from 2013 to 2025.

Live app: https://nyc-property-dashboard-xi9u.onrender.com/

(The app is hosted on a free Render instance, so the first load can take about a minute.)

## What it shows

The dashboard is built on about 498,000 residential property sales in the five boroughs from 2013 to 2025. Each sale is matched to its ZIP code, and ZIP-level data is added for household income, school rankings, arrests and crime, and subway access.

Main views:

- KPI cards for the selected years and borough
- A ZIP code map of median sale price
- Price trends over time, with a property type filter (1-Family, 2-Family, and so on)
- Four scatter plots comparing ZIP-level price with median household income, school ranking, crime (with a crime type dropdown), and distance to the nearest subway station
- A monthly section showing seasonal patterns in price and transaction volume

Filters for year range and borough apply across the charts.

## Data sources

The data comes from online open data sources. The school rankings were compiled by the team from public school rankings.

| Dataset | File in this repo | Source |
|---|---|---|
| Property sales, 2013 to 2025 | `Datasets/df_master.csv.gz` | [NYC Department of Finance, Annualized Sales](https://www.nyc.gov/site/finance/property/property-annualized-sales-update.page), yearly files by borough, 2013 to 2025 |
| Median household income by ZIP | `Datasets/df_income.csv` | Online open data sources |
| School rankings | `Datasets/df_schools_all.csv` | Compiled by the team from public school rankings |
| Arrests by ZIP (2025) | `Datasets/arrest_per_zip.csv`, `Datasets/arrest_zip_enhanced.csv` | [NYPD Arrest Data (Year to Date)](https://data.cityofnewyork.us/Public-Safety/NYPD-Arrest-Data-Year-to-Date-/uip8-fykc), NYC Open Data, downloaded February 28, 2026 |
| Major felony counts by borough, 2025 | `Datasets/arrest_zip_enhanced.csv` | NYPD CompStat reports, seven major felonies by precinct, Q1 to Q4 2025 |
| Subway stations | `Datasets/df_subway.csv` | [MTA Subway Stations](https://data.ny.gov/Transportation/MTA-Subway-Stations/39hk-dx4f), New York State Open Data, downloaded February 28, 2026 |
| ZIP code boundaries | loaded at runtime | [fedhere/PUI2015_EC](https://raw.githubusercontent.com/fedhere/PUI2015_EC/master/mam1612_EC/nyc-zip-code-tabulation-areas-polygons.geojson) |

`Datasets/df_zip_centroids.csv` holds the center point of each ZIP code and the distance to its nearest subway station, which was calculated with a KD-Tree nearest neighbor search (SciPy `cKDTree`). Crime per 10,000 people uses 2025 CompStat totals divided by borough population.

Raw source files are not included in this repo because of their size. The files in `Datasets/` are cleaned and reduced versions used by the app.

## Data preparation

`notebooks/data_prep.ipynb` shows how the data was prepared: loading the yearly sales files (about 1.1 million rows), filtering to residential sales and removing outliers and duplicates (about 498,000 rows), joining ZIP-level income, school, crime, and subway data, the KD-Tree calculations, and reducing `df_master.csv.gz` to the columns the app uses (about 2 MB). Chart outputs were removed to keep the file small. The raw files it reads are not in this repo, so it will not run as is.

## Limitations

- School rankings were compiled by the team from public school rankings. They do not come from one official source, so the ranking method may differ between schools.

## Tech stack

- Python
- Dash and Plotly for the app and charts
- pandas and NumPy for data processing
- SciPy (`cKDTree`) for the nearest subway station calculation
- Flask-Caching to cache callback results
- Gunicorn, deployed on Render

## Run locally

```bash
git clone https://github.com/xixi0817/nyc_property_dashboard.git
cd nyc_property_dashboard
pip install -r requirements.txt
python app.py
```

Then open http://localhost:8051 in a browser. The app needs an internet connection on startup to load the ZIP code boundary file.

## Team

Group 19, Baruch College CIS 9655 Data Visualization, Spring 2026

- Xixi Lin
- Jiahuan Wu
- Victor Louie
- Chhin Lama
