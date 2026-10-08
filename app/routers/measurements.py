"""Measurements API endpoints."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    MeasurementsSummaryResponse,
    AggregateMeasurementSummary,
)
from app.services.storage import storage_service

router = APIRouter(prefix="/files", tags=["Measurements"])


@router.get(
    "/{id}/measurements/",
    response_model=MeasurementsSummaryResponse,
    summary="Get Feature Measurements",
    description="Returns detailed measurement information for features in the specified file, "
                "including polygon areas, linestring lengths, perimeter, geodesic comparisons, "
                "and aggregate summaries."
)
async def get_file_measurements(
    id: str,
    geometry_type: Optional[str] = Query(
        None,
        description="Filter by geometry type: 'Polygon', 'LineString', 'Point', etc."
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=5000,
        description="Maximum number of features to return (for pagination)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Pagination offset index"
    ),
):
    """Returns measurements for the features in the uploaded file."""
    record = storage_service.get_file(id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found."
        )

    full_summary = storage_service.get_measurements_summary(id)
    if not full_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Measurements not available for file '{id}'."
        )

    # Apply filtering or pagination if requested
    if geometry_type or limit is not None or offset > 0:
        filtered_features = storage_service.get_features(
            file_id=id,
            geometry_type=geometry_type,
            limit=limit,
            offset=offset,
        )
        # Return response with filtered features but retaining overall file metadata
        return MeasurementsSummaryResponse(
            file_id=full_summary.file_id,
            filename=full_summary.filename,
            feature_count=full_summary.feature_count,
            crs=full_summary.crs,
            projected_crs_used=full_summary.projected_crs_used,
            summary=full_summary.summary,
            features=filtered_features,
        )

    return full_summary


@router.get(
    "/{id}/measurements/summary",
    response_model=AggregateMeasurementSummary,
    summary="Get File Aggregate Measurements Summary",
    description="Returns high-level totals (total area, total length, feature counts) without feature geometry payloads."
)
async def get_measurements_aggregate(id: str):
    """Returns high-level aggregate measurement totals."""
    full_summary = storage_service.get_measurements_summary(id)
    if not full_summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID '{id}' was not found."
        )
    return full_summary.summary
