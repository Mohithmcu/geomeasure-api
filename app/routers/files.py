"""File management and upload endpoints."""

import io
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.models.schemas import (
    FileInfoResponse,
    FileListResponse,
    GeoJSONFeatureCollection,
    GeoJSONFeature,
)
from app.services.processor import processor
from app.services.storage import storage_service

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/",
    response_model=FileInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Process Geospatial File",
    description="Accepts either a .zip archive containing an ESRI Shapefile or a .kml / .kmz file. "
                "Processes features, detects CRS, transforms to projected system, and computes measurements."
)
async def upload_file(
    file: UploadFile = File(..., description="Geospatial file (.zip Shapefile, .kml, or .kmz)")
):
    """Uploads and processes a geospatial file."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename."
        )

    filename = Path(file.filename).name
    ext = Path(filename).suffix.lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Accepted formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    file_type = "shapefile" if ext == ".zip" else "kml"

    # Allocate file record and save content
    temp_content = await file.read()
    file_size = len(temp_content)

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
        )

    file_id = storage_service.create_file_record(
        filename=filename,
        file_size_bytes=file_size,
        file_type=file_type,
    )

    dest_path = settings.UPLOAD_DIR / f"{file_id}_{filename}"
    with open(dest_path, "wb") as f_out:
        f_out.write(temp_content)

    # Process file synchronously for immediate API response
    result = processor.process_file(file_id=file_id, file_path=dest_path, filename=filename)

    return result


@router.get(
    "/{id}/",
    response_model=FileInfoResponse,
    summary="Get File Information",
    description="Returns metadata and processing status for an uploaded file by ID."
)
async def get_file_info(id: str):
    """Returns information about an uploaded file."""
    info = storage_service.get_file(id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found."
        )
    return info


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List Uploaded Files",
    description="Returns all uploaded files sorted by newest first."
)
async def list_files():
    """Lists all uploaded files."""
    files = storage_service.list_files()
    return FileListResponse(total=len(files), files=files)


@router.delete(
    "/{id}/",
    summary="Delete File",
    description="Deletes an uploaded file and all associated measurements."
)
async def delete_file(id: str):
    """Deletes an uploaded file by ID."""
    deleted = storage_service.delete_file(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found."
        )
    return {"status": "success", "message": f"File '{id}' deleted successfully."}


@router.get(
    "/{id}/geojson/",
    summary="Get File as GeoJSON FeatureCollection",
    description="Returns full GeoJSON with geometric coordinates and computed measurements in properties for map rendering."
)
async def get_file_geojson(id: str):
    """Returns standard GeoJSON FeatureCollection for interactive web mapping."""
    info = storage_service.get_file(id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found."
        )

    features = storage_service.get_features(id)
    geojson_features = []

    for feat in features:
        # Merge properties and measurements for clean GIS consumption
        combined_props = dict(feat.properties)
        combined_props["__feature_id"] = feat.feature_id
        combined_props["__geometry_type"] = feat.geometry_type
        combined_props["__measurements"] = feat.measurements.model_dump()

        geojson_features.append(
            GeoJSONFeature(
                id=feat.feature_id,
                geometry=feat.geometry,
                properties=combined_props,
            )
        )

    return GeoJSONFeatureCollection(
        name=info.filename,
        crs={"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        features=geojson_features,
    )


@router.post(
    "/load-sample/{sample_name}",
    response_model=FileInfoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Load Bundled Sample File",
    description="Instantly loads and processes pre-packaged sample geospatial datasets."
)
async def load_sample(sample_name: str):
    """Loads a pre-packaged sample dataset for instant one-click testing."""
    sample_files = {
        "parcels": ("sample_land_parcels.zip", "shapefile"),
        "pipelines": ("sample_utility_network.kml", "kml"),
        "points": ("sample_points_of_interest.kml", "kml"),
    }

    if sample_name not in sample_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown sample '{sample_name}'. Available samples: {', '.join(sample_files.keys())}"
        )

    filename, file_type = sample_files[sample_name]
    sample_path = settings.SAMPLES_DIR / filename

    if not sample_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample asset '{filename}' is not found on disk."
        )

    content = sample_path.read_bytes()
    file_id = storage_service.create_file_record(
        filename=filename,
        file_size_bytes=len(content),
        file_type=file_type,
    )

    dest_path = settings.UPLOAD_DIR / f"{file_id}_{filename}"
    dest_path.write_bytes(content)

    return processor.process_file(file_id=file_id, file_path=dest_path, filename=filename)


@router.get(
    "/{id}/export/csv",
    summary="Export Feature Measurements as CSV",
    description="Downloads a tabular CSV report of all feature measurements."
)
async def export_csv(id: str):
    """Exports measurements as a CSV spreadsheet."""
    info = storage_service.get_file(id)
    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    features = storage_service.get_features(id)
    output = io.StringIO()
    output.write("Feature_ID,Geometry_Type,Area_m2,Area_km2,Area_Acres,Perimeter_m,Length_m,Length_km,Length_Miles,Geodesic_Area_m2,Geodesic_Length_m,Projected_CRS\n")

    for feat in features:
        m = feat.measurements
        area_m2 = m.area.sq_meters if m.area else ""
        area_km2 = m.area.sq_kilometers if m.area else ""
        area_ac = m.area.acres if m.area else ""
        perim_m = m.perimeter.meters if m.perimeter else ""
        len_m = m.length.meters if m.length else ""
        len_km = m.length.kilometers if m.length else ""
        len_mi = m.length.miles if m.length else ""
        geo_area = m.geodesic_area_sq_m or ""
        geo_len = m.geodesic_length_m or ""
        proj_crs = m.projected_crs

        output.write(
            f'"{feat.feature_id}","{feat.geometry_type}",{area_m2},{area_km2},{area_ac},{perim_m},{len_m},{len_km},{len_mi},{geo_area},{geo_len},"{proj_crs}"\n'
        )

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{info.filename}_measurements.csv"'}
    )
