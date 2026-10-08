# 🌍 GeoMeasure API — Geospatial Measurement & Projection Engine

[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![GIS Engine](https://img.shields.io/badge/GIS%20Engine-Shapely%202.x%20%7C%20PyProj-success.svg)](https://shapely.readthedocs.io/)
[![Tests](https://img.shields.io/badge/Tests-17%20Passed-brightgreen.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

A production-grade backend service and interactive GIS dashboard that accepts geospatial files (**ESRI Shapefiles** in `.zip` archives and **OGC KML / KMZ** files), extracts vector features, detects native coordinate reference systems (CRS), automatically reprojects geographic coordinates to optimal metric projected coordinate reference systems (**Universal Transverse Mercator - UTM**), and computes high-precision geometric measurements.

---

## 📌 Executive Summary

Geographic files often use latitude and longitude coordinates in degrees (such as **WGS 84 / EPSG:4326**). **Calculating area or distance directly using latitude and longitude degrees is mathematically incorrect** because degree distances shrink as you move away from the equator.

**GeoMeasure API solves this problem automatically:**
1. It reads your uploaded Shapefile or KML file.
2. It detects the native coordinate system.
3. If coordinates are in degrees (geographic), it calculates the center point of the feature, identifies the exact local **UTM Zone**, and transforms the geometry into a metric coordinate system (meters).
4. It calculates **true planar area and perimeter** for Polygons, **true length** for LineStrings, and handles Points gracefully without crashing.
5. It renders the features on a sleek, interactive **Leaflet map visualizer** with one-click sample datasets.

---

## 📑 Table of Contents

- [Key Features](#-key-features)
- [How It Works (Architecture Explained Simply)](#-how-it-works-architecture-explained-simply)
  - [1. Application Structure](#1-application-structure)
  - [2. File Processing Flow](#2-file-processing-flow)
  - [3. Why We Cannot Measure in Degrees (CRS Handling)](#3-why-we-cannot-measure-in-degrees-crs-handling)
  - [4. Dynamic UTM Selection Strategy](#4-dynamic-utm-selection-strategy)
  - [5. Measurement Calculation Flow](#5-measurement-calculation-flow)
- [Local Setup & Installation](#-local-setup--installation)
  - [Prerequisites](#prerequisites)
  - [Standard Local Run (Windows / macOS / Linux)](#standard-local-run-windows--macos--linux)
  - [Docker Run (One-Command)](#docker-run-one-command)
  - [Running the Automated Tests](#running-the-automated-tests)
- [API Documentation & Examples](#-api-documentation--examples)
  - [Endpoint Overview](#endpoint-overview)
  - [1. Upload File (`POST /api/files/`)](#1-upload-geospatial-file-post-apifiles)
  - [2. File Information (`GET /api/files/{id}/`)](#2-get-file-information-get-apifilesid)
  - [3. Feature Measurements (`GET /api/files/{id}/measurements/`)](#3-get-feature-measurements-get-apifilesidmeasurements)
  - [4. GeoJSON Representation (`GET /api/files/{id}/geojson/`)](#4-get-geojson-representation-get-apifilesidgeojson)
  - [5. Export to CSV (`GET /api/files/{id}/export/csv`)](#5-export-measurements-to-csv-get-apifilesidexportcsv)
  - [6. Health Check (`GET /api/health`)](#6-system-health-check-get-apihealth)
- [Interactive Web Visualizer](#-interactive-web-visualizer)
- [Design Decisions & Alternatives Considered](#-design-decisions--alternatives-considered)
- [Learnings & Future Scope](#-learnings--future-scope)

---

## ✨ Key Features

- **Multi-Format Ingestion**: Supports `.zip` Shapefiles (containing `.shp`, `.shx`, `.dbf`, `.prj`) and `.kml` / `.kmz` vector files.
- **Automated Metric Reprojection**: Converts geographic degrees (`EPSG:4326`) into local metric UTM zones before measurement.
- **Graceful Geometry Support**:
  - **Polygon / MultiPolygon**: Area ($m^2$, $km^2$, hectares, acres, $ft^2$) and boundary perimeter ($m$, $km$, miles, $ft$).
  - **LineString / MultiLineString**: Linear distance ($m$, $km$, miles, $ft$).
  - **Point / MultiPoint**: Gracefully identified as 0-dimensional anchors with informational notes rather than failing.
  - **Malformed Geometries**: Automatically repaired using `shapely.validation.make_valid`.
- **Dual Calculations**: Computes both projected planar measurements and **WGS 84 ellipsoidal geodesic measurements** (`pyproj.Geod`) for comparison.
- **Interactive Web Map**: Built-in Leaflet GIS client with **Dark Canvas**, **Esri Satellite Imagery**, and **OpenStreetMap** layers.
- **Zero Database Setup**: Includes self-contained, thread-safe persistence with zero external database configuration required.
- **Full OpenAPI Swagger Docs**: Auto-generated interactive documentation at `/docs` and `/redoc`.

---

## 🧠 How It Works (Architecture Explained Simply)

### 1. Application Structure

The codebase is organized into clean, modular layers following standard backend patterns:

```text
companyasses/
├── app/
│   ├── main.py                   # FastAPI initialization, CORS, static routes
│   ├── config.py                 # App settings, directory paths, file size limits
│   ├── models/
│   │   └── schemas.py            # Pydantic data validation and response contracts
│   ├── services/
│   │   ├── crs_service.py        # CRS parsing, UTM zone determination, reprojection
│   │   ├── measurement_service.py# Area, length, perimeter, and unit calculations
│   │   ├── shapefile_parser.py   # Safe zip extraction and PyShp record parser
│   │   ├── kml_parser.py         # KML/KMZ XML parser extracting features & attributes
│   │   ├── storage.py            # Thread-safe metadata & feature storage
│   │   └── processor.py          # Unified processing orchestrator
│   └── routers/
│       ├── files.py              # Upload, info, GeoJSON, and CSV export endpoints
│       ├── measurements.py       # Measurement queries and geometry filtering
│       └── health.py             # System diagnostics & library versions
├── static/                       # Web Dashboard (HTML, CSS, JS)
│   ├── index.html                # Professional single-page GIS workstation
│   ├── css/styles.css            # Custom CSS design system (Slate/Emerald/Indigo)
│   └── js/app.js                 # Reactive Leaflet map controller
├── samples/                      # 3 Bundled test datasets
│   ├── sample_land_parcels.zip   # Cadastre parcels (Shapefile, Fresno CA)
│   ├── sample_utility_network.kml# Infrastructure pipelines & facility polygons
│   └── sample_points_of_interest.kml # Survey benchmarks (Points)
├── tests/                        # 17 automated unit and integration tests
├── Dockerfile                    # Production Docker container image
├── docker-compose.yml            # Docker Compose orchestration
├── requirements.txt              # Production Python dependencies
└── README.md                     # Comprehensive project documentation
```

---

### 2. File Processing Flow

```text
1. User Upload (ZIP or KML)
         │
         ▼
2. Validation & Stream Save (Upload limit: 50MB)
         │
         ▼
3. Parser Selection:
   ├─ If .zip ──► ShapefileParser extracts .shp, .shx, .dbf, .prj
   └─ If .kml ──► KMLParser parses XML Placemarks & ExtendedData
         │
         ▼
4. Coordinate Reference System (CRS) Analysis
   ├─ Source CRS detected (e.g. from .prj file or default EPSG:4326)
   └─ Is it Geographic (degrees)?
         ├─ YES ──► Dynamically find optimal UTM Zone & reproject geometry to meters
         └─ NO  ──► Geometry is already projected in linear meters/feet
         │
         ▼
5. Geometry Measurement Engine
   ├─ Polygon    ──► Compute Planar Area & Perimeter (+ WGS84 Geodesic Area)
   ├─ LineString ──► Compute Planar Length (+ WGS84 Geodesic Length)
   └─ Point      ──► Mark as zero-dimensional anchor (No crash, clear note)
         │
         ▼
6. Storage & JSON Response Return
```

---

### 3. Why We Cannot Measure in Degrees (CRS Handling)

A geographic coordinate system like **EPSG:4326 (WGS 84)** places points on an ellipsoidal model of Earth using angular units: **Latitude ($-90^\circ$ to $+90^\circ$)** and **Longitude ($-180^\circ$ to $+180^\circ$)**.

```text
               North Pole (90° N) -> 1° Longitude = 0 km
                     / \
                    /   \
    London (51.5° N)  ─ 1° Longitude ≈ 69.4 km
                  /       \
  Equator (0° N) ─────────── 1° Longitude ≈ 111.32 km
```

- At the **Equator**, $1^\circ$ of longitude is approximately **$111.32\text{ km}$**.
- At **London ($51.5^\circ\text{ N}$)**, $1^\circ$ of longitude shrinks to approximately **$69.4\text{ km}$**.
- At the **Poles**, $1^\circ$ of longitude converges to **$0\text{ km}$**.

If software calculates the area of a polygon using raw degree coordinates:
$$\text{Area} = \Delta \text{longitude} \times \Delta \text{latitude} = 0.00015\text{ degrees}^2$$
This number is **physically meaningless** and cannot be converted into square meters with a single multiplier because the scale changes at every latitude.

**Therefore, the geometry must be projected onto a flat metric surface before calculating measurements.**

---

### 4. Dynamic UTM Selection Strategy

The **Universal Transverse Mercator (UTM)** system divides the Earth between $80^\circ\text{ S}$ and $84^\circ\text{ N}$ into **60 longitudinal zones**, each $6^\circ$ wide. Within each zone, scale distortion is constrained to **less than $0.1\%$**, making it the global standard for engineering-grade land and route measurement.

Our application selects the projected CRS automatically:
1. It calculates the centroid $(\text{lon}, \text{lat})$ of the geometry in WGS 84.
2. It determines the 6-degree UTM zone index:
   $$\text{Zone} = \left\lfloor \frac{\text{longitude} + 180^\circ}{6^\circ} \right\rfloor + 1 \quad (\text{clamped between } 1 \text{ and } 60)$$
3. It assigns the appropriate EPSG authority code:
   - **Northern Hemisphere ($\text{lat} \ge 0^\circ$)**: $\text{EPSG Code} = 32600 + \text{Zone}$ *(e.g., California is Zone 11N $\rightarrow$ `EPSG:32611`, UK is Zone 30N $\rightarrow$ `EPSG:32630`)*
   - **Southern Hemisphere ($\text{lat} < 0^\circ$)**: $\text{EPSG Code} = 32700 + \text{Zone}$ *(e.g., Sydney Australia is Zone 56S $\rightarrow$ `EPSG:32756`)*
   - **Polar Regions ($|\text{lat}| > 84^\circ$)**: Switches to Universal Polar Stereographic (**UPS North `EPSG:3413`** / **UPS South `EPSG:3031`**).
4. The coordinates are reprojected from source to target UTM using `pyproj.Transformer(from_crs, to_crs, always_xy=True)` using modern vectorized arrays via `shapely.transform`.

---

### 5. Measurement Calculation Flow

Once in the projected metric coordinate system:
- **Polygons**:
  - `projected_geom.area` gives the exact planar area in **square meters ($m^2$)**.
  - `projected_geom.length` gives the exact boundary perimeter in **meters ($m$)**.
  - Multi-unit conversions:
    - $\text{Square Kilometers} = m^2 / 1,000,000$
    - $\text{Hectares} = m^2 / 10,000$
    - $\text{Acres} = m^2 \times 0.000247105$
    - $\text{Square Feet} = m^2 \times 10.7639$
- **LineStrings**:
  - `projected_geom.length` gives the linear path distance in **meters ($m$)**.
  - Multi-unit conversions:
    - $\text{Kilometers} = m / 1,000$
    - $\text{Miles} = m \times 0.000621371$
    - $\text{Feet} = m \times 3.28084$
- **Points**:
  - Points have zero area and zero length.
  - Returns `supported: false` with the status note: `"Point features represent 0-dimensional coordinates. Measurement not applicable."`
- **Geodesic Ellipsoidal Calculations**:
  - In addition to planar UTM measurements, the service computes geodesic distance and area directly on the WGS 84 ellipsoid using `pyproj.Geod(ellps='WGS84')` (`geometry_area_perimeter` and `geometry_length`). This provides reviewers with a direct cross-validation metric.

---

## 🚀 Local Setup & Installation

### Prerequisites
- Python **3.10+** (tested and verified on Python 3.10, 3.11, 3.12, and 3.14)
- `pip` package manager
- *(Optional)* Docker and Docker Compose

---

### Standard Local Run (Windows / macOS / Linux)

#### 1. Clone the repository and navigate into the folder:
```bash
git clone <your-repository-url>
cd companyasses
```

#### 2. Create and activate a virtual environment:
**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```
**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Install dependencies:
```bash
pip install -r requirements.txt
```

#### 4. Generate the bundled sample datasets:
```bash
python generate_samples.py
```
*(This creates `sample_land_parcels.zip`, `sample_utility_network.kml`, and `sample_points_of_interest.kml` inside the `samples/` directory).*

#### 5. Start the application server:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 6. Open the application:
- **Interactive Web Visualizer**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

### Docker Run (One-Command)

If you prefer using Docker, build and run the container with:

```bash
docker compose up --build
```
The server will be available at [http://localhost:8000](http://localhost:8000).

---

### Running the Automated Tests

The repository includes a comprehensive automated test suite with **17 test cases**:

```bash
python -m pytest -v
```

**Test Execution Summary:**
```text
tests/test_api.py::test_health_check PASSED                              [  5%]
tests/test_api.py::test_upload_shapefile_and_get_measurements PASSED     [ 11%]
tests/test_api.py::test_upload_kml_and_filtering PASSED                  [ 17%]
tests/test_api.py::test_upload_invalid_file_format PASSED                [ 23%]
tests/test_api.py::test_get_nonexistent_file PASSED                      [ 29%]
tests/test_crs_service.py::test_parse_crs_epsg_code PASSED               [ 35%]
tests/test_crs_service.py::test_parse_crs_integer_string PASSED          [ 41%]
tests/test_crs_service.py::test_parse_crs_fallback PASSED                [ 47%]
tests/test_crs_service.py::test_determine_optimal_utm_northern_hemisphere PASSED [ 52%]
tests/test_crs_service.py::test_determine_optimal_utm_southern_hemisphere PASSED [ 58%]
tests/test_crs_service.py::test_determine_optimal_polar_regions PASSED   [ 64%]
tests/test_kml_parser.py::test_parse_sample_pipelines PASSED             [ 70%]
tests/test_kml_parser.py::test_parse_sample_points PASSED                [ 76%]
tests/test_measurement_service.py::test_polygon_area_and_perimeter PASSED [ 82%]
tests/test_measurement_service.py::test_linestring_length PASSED         [ 88%]
tests/test_measurement_service.py::test_point_graceful_handling PASSED   [ 94%]
tests/test_shapefile_parser.py::test_parse_sample_parcels PASSED         [100%]
============================= 17 passed in 0.73s ==============================
```

---

## 📡 API Documentation & Examples

### Endpoint Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/files/` | Upload and process a `.zip` Shapefile or `.kml`/`.kmz` file |
| `GET` | `/api/files/{id}/` | Get summary information and status of an uploaded file |
| `GET` | `/api/files/{id}/measurements/` | Get feature measurements with optional geometry type filter |
| `GET` | `/api/files/{id}/measurements/summary` | Get high-level totals without individual feature geometry payloads |
| `GET` | `/api/files/{id}/geojson/` | Get standard GeoJSON FeatureCollection for WebGIS clients |
| `GET` | `/api/files/{id}/export/csv` | Download measurements as a CSV spreadsheet |
| `GET` | `/api/files/` | List all uploaded files |
| `DELETE`| `/api/files/{id}/` | Delete an uploaded file and its metadata |
| `POST` | `/api/files/load-sample/{sample_name}` | One-click loader for bundled sample datasets |
| `GET` | `/api/health` | Operational diagnostic check |

---

### 1. Upload Geospatial File (`POST /api/files/`)

Uploads a `.zip` Shapefile or `.kml` file. Features are immediately extracted, reprojected, and measured.

#### cURL Request:
```bash
curl -X POST "http://127.0.0.1:8000/api/files/" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@samples/sample_land_parcels.zip"
```

#### Response (`201 Created`):
```json
{
  "id": "e4f8a91b",
  "filename": "sample_land_parcels.zip",
  "feature_count": 4,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "file_size_bytes": 1420,
  "file_type": "shapefile",
  "geometry_summary": {
    "Polygon": 4
  },
  "projected_crs": "EPSG:32611",
  "created_at": "2026-10-08T13:20:00.000000Z",
  "total_area_sq_m": 5216460.20,
  "total_length_m": null,
  "error_message": null
}
```

---

### 2. Get File Information (`GET /api/files/{id}/`)

Returns information about the uploaded file complying strictly with the assessment specification.

#### cURL Request:
```bash
curl -X GET "http://127.0.0.1:8000/api/files/e4f8a91b/" \
  -H "accept: application/json"
```

#### Response (`200 OK`):
```json
{
  "id": "e4f8a91b",
  "filename": "sample_land_parcels.zip",
  "feature_count": 4,
  "crs": "EPSG:4326",
  "status": "COMPLETED"
}
```

---

### 3. Get Feature Measurements (`GET /api/files/{id}/measurements/`)

Returns measurements for features in the file. Supports filtering by geometry type (`Polygon`, `LineString`, `Point`) and pagination via `limit` and `offset`.

#### cURL Request:
```bash
curl -X GET "http://127.0.0.1:8000/api/files/e4f8a91b/measurements/?geometry_type=Polygon" \
  -H "accept: application/json"
```

#### Response (`200 OK`):
```json
{
  "file_id": "e4f8a91b",
  "filename": "sample_land_parcels.zip",
  "feature_count": 4,
  "crs": "EPSG:4326",
  "projected_crs_used": "EPSG:32611",
  "summary": {
    "total_features": 4,
    "measured_features": 4,
    "unmeasured_features": 0,
    "total_area_sq_m": 5216460.20,
    "total_area_sq_km": 5.21646,
    "total_area_hectares": 521.646,
    "total_area_acres": 1289.0142,
    "total_length_m": 0.0,
    "total_length_km": 0.0,
    "total_length_miles": 0.0,
    "geometry_breakdown": {
      "Polygon": 4
    }
  },
  "features": [
    {
      "feature_id": "P-101",
      "geometry_type": "Polygon",
      "crs": "EPSG:4326",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-119.78, 36.74], [-119.78, 36.748], [-119.77, 36.748], [-119.77, 36.74], [-119.78, 36.74]]]
      },
      "properties": {
        "PARCEL_ID": "P-101",
        "LAND_USE": "Vineyard",
        "FARMER": "Valley Vista Estates",
        "IRRIGATED": "YES"
      },
      "measurements": {
        "supported": true,
        "geometry_type": "Polygon",
        "projected_crs": "EPSG:32611",
        "projected_crs_name": "WGS 84 / UTM zone 11N",
        "area": {
          "sq_meters": 782469.03,
          "sq_kilometers": 0.782469,
          "hectares": 78.2469,
          "acres": 193.3523,
          "sq_feet": 8422421.21
        },
        "perimeter": {
          "meters": 3543.12,
          "kilometers": 3.5431,
          "miles": 2.2016,
          "feet": 11624.41
        },
        "geodesic_area_sq_m": 782458.12,
        "notes": "Measurements calculated in projected metric CRS. Geodesic area computed on WGS84 ellipsoid."
      },
      "centroid": [-119.775, 36.744],
      "bbox": [-119.78, 36.74, -119.77, 36.748]
    }
  ]
}
```

---

### 4. Get GeoJSON Representation (`GET /api/files/{id}/geojson/`)

Returns the vector features formatted as standard GeoJSON with calculated measurements embedded directly in the feature properties, ready for direct import into QGIS, ArcGIS, or Mapbox.

---

### 5. Export Measurements to CSV (`GET /api/files/{id}/export/csv`)

Downloads a spreadsheet containing Feature IDs, geometry types, areas, lengths, perimeters, and projected CRS codes.

---

### 6. System Health Check (`GET /api/health`)

```bash
curl -X GET "http://127.0.0.1:8000/api/health"
```
```json
{
  "status": "healthy",
  "service": "Geospatial File Measurement API",
  "version": "1.0.0",
  "python_version": "3.14.4",
  "geospatial_libraries": {
    "shapely": "2.2.0",
    "pyproj": "3.8.0",
    "pyshp": "3.1.6"
  },
  "storage_writable": true,
  "supported_formats": [".zip (Shapefile)", ".kml", ".kmz"]
}
```

---

## 🎨 Interactive Web Visualizer

When you navigate to `http://127.0.0.1:8000`, the built-in GIS client provides:

1. **Upload Dropzone**: Drag and drop any `.zip` Shapefile or `.kml` file with a live upload progress indicator.
2. **One-Click Sample Previews**:
   - 🌾 **Land Parcels (Fresno, CA)**: Agricultural cadastre polygons in UTM Zone 11N.
   - ⚡ **Utility Pipelines & Easements (London, UK)**: Gas & water transmission polylines and station easements in UTM Zone 30N.
   - 📍 **Geodetic Survey Benchmarks (Bangalore, India)**: Point features demonstrating graceful handling without crashing.
3. **Interactive Leaflet Map**:
   - Vector styling: Polygons in **Emerald Green**, LineStrings in **Indigo Blue**, Points in **Amber Orange**.
   - Hover tooltips and auto-zoom to dataset bounds.
   - Base map switcher: **Dark Canvas**, **Esri World Satellite Imagery**, and **OpenStreetMap Standard**.
4. **Unit Switcher Chips**: One-click switching between Metric ($m^2$, $km^2$, $\text{ha}$, $m$, $km$) and Imperial ($\text{ac}$, $\text{ft}^2$, $\text{mi}$, $\text{ft}$).
5. **Feature Inspector Drawer**: Click any feature on the map or in the table to inspect its calculated area, length, geodesic validation, and full attribute key-values.
6. **Data Explorer Table**: Filter by geometry type, search across attributes, and export to CSV or GeoJSON.

---

## 💡 Design Decisions & Alternatives Considered

| Technical Decision | Chosen Solution | Alternative Considered | Rationale & Trade-offs |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** | Django + DRF | FastAPI provides native asynchronous I/O, strict data validation with Pydantic 2, automatic OpenAPI 3.1 Swagger documentation, and high throughput. Django was considered but introduces heavy ORM migrations unnecessary for this microservice. |
| **Geospatial Engine** | **PyProj + Shapely 2.x + PyShp** | GDAL / Fiona / GeoPandas | Native GDAL C-bindings frequently encounter binary compatibility issues across different OS distributions. Shapely 2.x and PyProj bundle precompiled GEOS and PROJ binaries, guaranteeing reliability on Windows, Linux, and macOS without system library conflicts. |
| **KML Parsing** | **Dual Engine (XML + FastKML)** | FastKML exclusively | KML files generated by different GIS software (Google Earth, ArcGIS, QGIS) frequently use divergent XML namespace declarations. A namespace-agnostic XML fallback ensures that nested Placemarks, Polygons, LineStrings, and ExtendedData parse consistently. |
| **Projection Strategy** | **Dynamic Local UTM (6° Zones)** | Web Mercator (EPSG:3857) | Web Mercator severely distorts distances and areas away from the equator (Greenland appears larger than Africa). Local UTM zones constrain scale distortion to $< 0.1\%$ within each zone. |
| **Calculation Accuracy** | **Planar UTM + Geodesic (WGS 84)** | Planar UTM only | Providing both planar measurements in projected meters and ellipsoidal geodesic measurements (`pyproj.Geod`) allows reviewers to cross-validate results and assess scale-factor variations. |
| **Data Persistence** | **In-Memory Cache + JSON Disk Storage** | PostgreSQL / PostGIS | Kept the service zero-configuration and immediately executable without requiring an external database server to be installed. State persists across server restarts. |

---

## 📈 Learnings & Future Scope

### Key Learnings
1. **Coordinate Axis Order Standards**: In GIS, some EPSG authorities define coordinates as $(\text{latitude}, \text{longitude})$ while others define them as $(\text{longitude}, \text{latitude})$. Using `always_xy=True` in `pyproj.Transformer` was essential to enforce strict $(X, Y) = (\text{lon}, \text{lat})$ ordering and prevent flipped-axis errors.
2. **Shapefile Polygon Ring Winding**: In the ESRI Shapefile specification, exterior boundary rings must be wound clockwise, whereas GeoJSON standards require counter-clockwise outer rings. Normalizing polygon orientation ensures full cross-standard compatibility.
3. **Projection vs. Geodesic Nuance**: On large geometries that span across multiple UTM zones, geodesic calculations on the reference ellipsoid provide higher accuracy than single-zone planar projections, reinforcing the value of providing dual calculations.

### Future Scope & Roadmap
1. **Asynchronous Worker Queues**: For very large multi-gigabyte spatial datasets (such as national cadastral maps), integrate Celery or ARQ with Redis for background asynchronous processing and WebSocket progress streaming.
2. **Cloud Storage Integration**: Add cloud storage drivers (AWS S3, Google Cloud Storage, Azure Blob Storage) for scalable file uploads.
3. **PostGIS & Spatial Indexing**: Add PostGIS support with R-Tree / GiST spatial indexing for fast bounding-box queries, spatial joins, and buffering.
4. **3D Surface Measurements with DEM**: Incorporate Digital Elevation Models (DEM GeoTIFFs) to calculate true 3D surface area and slope-adjusted path length in mountainous terrain.
5. **Modern Vector Formats**: Expand format ingestion to modern cloud-native formats such as **GeoPackage (`.gpkg`)**, **FlatGeobuf (`.fgb`)**, and **GeoParquet**.

---

## 📄 License
MIT License. Created for technical assessment evaluation.
