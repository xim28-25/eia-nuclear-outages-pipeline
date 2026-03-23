# EIA Nuclear Outages Pipeline
# BY: Ximena Andrade Luviano
A data pipeline that extracts Nuclear Outages data from the EIA Open Data API, stores it efficiently in Parquet files and a SQLite database, and provides analytics and query capabilities through a REST API and web interface.

## Project Structure

```
TechnicalChallenge/
├── Arkham/                              # Python virtual environment & backend
│   ├── dataConnector.py                 # Part 1 — EIA API connector & pipeline
│   ├── dataModel.py                     # Part 2 — Loads Parquet data into SQLite
│   ├── dataModel.sql                    # Part 2 — SQL schema (tables & indexes)
│   ├── nuclear_outages.db                       # SQLite database (auto-generated)
│   ├── data/                            # Parquet files (auto-generated)
│   │   ├── nuclear_us-nuclear-outages_*.parquet
│   │   ├── nuclear_facility-nuclear-outages_*.parquet
│   │   ├── nuclear_generator-nuclear-outages_*.parquet
│   │   └── resumen_*.json
│   ├── nuclear_outages_api/             # Django project settings
│   │   ├── settings.py
│   │   └── urls.py
│   ├── outages/                         # Part 3 — REST API app
│       ├── views.py                     # /api/data, /api/refresh, /api/analytics
│       └── urls.py                                         
│       
├── frontend/                            # Part 4 — React + Vite + Tailwind CSS
│   └── src/
│       ├── components/
│       │   ├── AnalyticsPanel.jsx       # Analytics tab
│       │   ├── DataTable.jsx            # Data table with sorting & filtering
│       │   ├── FilterBar.jsx            # Filter controls
│       │   ├── Navbar.jsx               # Navigation bar
│       │   └── Footer.jsx
│       └── App.jsx                      # Main component
├── docs/                                # ER diagram and documentation
│   └── er_diagram.png
└── README.md
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/xim28-25/eia-nuclear-outages-pipeline.git
cd eia-nuclear-outages-pipeline
```

### 2. Set up the Python environment

```bash
cd Arkham
python3 -m venv .
source bin/activate        # Mac/Linux
pip install requests pandas pyarrow django djangorestframework django-cors-headers pytest pytest-django
```

### 3. Set up your API key

```bash
export EIA_API_KEY="your_api_key_here"
```

> Get your free API key at: https://www.eia.gov/opendata/

### 4. Run the data pipeline

```bash
# Extract data from EIA API and save to Parquet
python dataConnector.py

# Create the SQLite database schema
sqlite3 nuclear_outages.db < dataModel.sql

# Load Parquet data into the database
python dataModel.py
```

### 5. Start the REST API

```bash
python manage.py runserver
# API available at http://127.0.0.1:8000/
```

### 6. Start the frontend

```bash
cd ../frontend
npm install
npm run dev
# UI available at http://localhost:5173/
```

---

## API Key Setup

The connector reads the API key from the `EIA_API_KEY` environment variable.

```bash
# Temporary (current session only)
export EIA_API_KEY="your_api_key_here"

# Permanent (add to your shell profile)
echo 'export EIA_API_KEY="your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

---

## API Endpoints

### `GET /api/data`

Returns filtered outage data with pagination.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `endpoint` | string | `us` | Dataset: `us`, `facility`, `generator` |
| `date_start` | date | — | Filter from date (YYYY-MM-DD) |
| `date_end` | date | — | Filter to date (YYYY-MM-DD) |
| `limit` | int | `100` | Records per page |
| `offset` | int | `0` | Pagination offset |

**Example:**
```bash
curl "http://127.0.0.1:8000/api/data?endpoint=us&limit=5"
```

```json
{
    "endpoint": "us",
    "total": 7022,
    "limit": 5,
    "offset": 0,
    "data": [
        {
            "id": 7022,
            "period": "2026-03-23",
            "capacity": 100013.0,
            "outage": 20500.657,
            "percentOutage": 20.5
        }
    ]
}
```

---

### `POST /api/refresh`

Triggers the full data pipeline in the background. Responds immediately while the pipeline runs asynchronously.

```bash
curl -X POST "http://127.0.0.1:8000/api/refresh"
```

```json
{
    "status": "ok",
    "message": "Pipeline iniciado. Los datos estarán disponibles en unos minutos."
}
```

---

### `GET /api/analytics`

Returns pre-computed analytics for a given dataset.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `endpoint` | string | `us` | Dataset: `us`, `facility`, `generator` |

**Example — National trend:**
```bash
curl "http://127.0.0.1:8000/api/analytics?endpoint=us"
```

```json
{
    "endpoint": "us-nuclear-outages",
    "created_at": "2026-03-23T18:44:11.351720+00:00",
    "analytics": {
        "total_registros": 7022,
        "periodo_inicio": "2007-01-01",
        "periodo_fin": "2026-03-23",
        "tendencia_mensual": {
            "2007-01": 3.25,
            "2021-02": 5.36,
            "2026-03": 14.21
        }
    }
}
```

**Example — Top 10 plants:**
```bash
curl "http://127.0.0.1:8000/api/analytics?endpoint=facility"
```

```json
{
    "analytics": {
        "top10_plantas_mayor_outage_historico_MW": {
            "Palo Verde": 2701243.99,
            "Browns Ferry": 2657406.88,
            "Donald C Cook": 2077208.36
        },
        "promedio_percentOutage_por_planta": {
            "Crystal River": 57.96,
            "Fort Calhoun": 34.15
        }
    }
}
```

---

## Data Model

The database contains 5 tables:

| Table | Description |
|---|---|
| `units` | Shared units of measurement (megawatts, percent) |
| `us_nuclear_outages` | Daily national aggregated outage data |
| `facility_nuclear` | Daily outage data per nuclear plant |
| `generator_nuclear` | Daily outage data per reactor/generator |
| `analytics` | Pre-computed analytics results per endpoint |

**Relationships:**
- `us_nuclear_outages.units_id` → `units.id`
- `facility_nuclear.units_id` → `units.id`
- `generator_nuclear.facility_id` → `facility_nuclear.id`
- `generator_nuclear.units_id` → `units.id`

![ER Diagram](docs/er_diagram.png)

---

## Running Tests

```bash
cd Arkham
pytest tests/ -v
```

---

## Assumptions Made

- The three EIA nuclear outage endpoints (`us`, `facility`, `generator`) represent different granularity levels of the same data — national, plant-level, and reactor-level respectively.
- All three endpoints share the same units (megawatts for capacity/outage, percent for percentOutage), so a single `units` lookup table is sufficient.
- The `outage` field (singular) is used consistently across all three endpoints — confirmed via API metadata.
- **Incremental extraction** is implemented — on subsequent runs, the pipeline only downloads data newer than the last record in the database, avoiding redundant API calls.
- SQLite was chosen for simplicity and portability. A production setup would use PostgreSQL or a cloud data warehouse.
- The `/refresh` endpoint runs the pipeline in a background thread to avoid HTTP timeouts, since a full extraction takes several minutes.
- The `analytics` table acts as an audit log — each pipeline run appends a new row with pre-computed results, allowing historical comparison of pipeline executions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data extraction | Python, `requests`, `pandas` |
| Storage | Parquet (`pyarrow`), SQLite |
| REST API | Django, Django REST Framework |
| Frontend | React, Vite, Tailwind CSS |
| Testing | pytest, pytest-django |