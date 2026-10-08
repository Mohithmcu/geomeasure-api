"""System health check and diagnostic endpoint."""

import sys
from fastapi import APIRouter
import pyproj
import shapely
import shapefile

from app.config import settings

router = APIRouter(prefix="", tags=["Health & System"])


@router.get("/health", summary="System Health & Diagnostics")
async def health_check():
    """Returns system status, active dependencies, and runtime diagnostics."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "python_version": sys.version.split(" ")[0],
        "geospatial_libraries": {
            "shapely": shapely.__version__,
            "pyproj": pyproj.__version__,
            "pyshp": shapefile.__version__,
        },
        "storage_writable": settings.UPLOAD_DIR.exists() and os_is_writable(settings.UPLOAD_DIR),
        "supported_formats": [".zip (Shapefile)", ".kml", ".kmz"],
    }


def os_is_writable(path) -> bool:
    import os
    return os.access(path, os.W_OK)
