"""Main FastAPI application entry point."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import files_router, measurements_router, health_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
# 🌍 Geospatial File Measurement API

A robust, production-grade geospatial measurement backend service and interactive dashboard.

## Capabilities:
- **Formats**: Upload `.zip` (Shapefile with .shp, .shx, .dbf, .prj) and `.kml` / `.kmz`.
- **Feature Extraction**: Extracts feature IDs, geometry types, GeoJSON representations, CRS, and attribute properties.
- **Graceful Geometry Support**: Calculates Area & Perimeter for Polygons, Length for LineStrings, and gracefully handles Points and collections without crashing.
- **Intelligent CRS Reprojection**: Detects source geographic coordinate systems (e.g. EPSG:4326) and automatically reprojects to optimal local projected coordinate reference systems (e.g. UTM zones) before computing metric measurements. Never calculates areas/distances in raw degrees!
- **Dual Calculations**: Provides planar projected measurements (m², km², ha, acres, meters, feet) and ellipsoidal geodesic calculations on the WGS84 ellipsoid.
- **Interactive Map Dashboard**: High-contrast, clean web UI with Leaflet visualization, unit switcher, and feature inspector.
    """,
    openapi_tags=[
        {"name": "Files", "description": "Endpoints for uploading, inspecting, and managing geospatial files."},
        {"name": "Measurements", "description": "Endpoints for extracting and computing geometric measurements."},
        {"name": "Health & System", "description": "Operational diagnostics and library statuses."},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for external client integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under /api
app.include_router(files_router, prefix=settings.API_PREFIX)
app.include_router(measurements_router, prefix=settings.API_PREFIX)
app.include_router(health_router, prefix=settings.API_PREFIX)

# Serve static web frontend if directory exists
static_dir = settings.BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "Geospatial File Measurement API is running. Visit /docs for Swagger UI."}
