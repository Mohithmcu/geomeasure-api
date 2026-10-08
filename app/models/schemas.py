"""Pydantic schemas and data transfer models for the API."""

from enum import Enum
from typing import Any, Optional, Union
from pydantic import BaseModel, Field


class FileStatus(str, Enum):
    """Lifecycle status of an uploaded geospatial file."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GeometryType(str, Enum):
    """Standard OGC geometry types."""
    POINT = "Point"
    MULTIPOINT = "MultiPoint"
    LINESTRING = "LineString"
    MULTILINESTRING = "MultiLineString"
    POLYGON = "Polygon"
    MULTIPOLYGON = "MultiPolygon"
    GEOMETRYCOLLECTION = "GeometryCollection"
    UNKNOWN = "Unknown"


class AreaUnits(BaseModel):
    """Area measurements across standard scientific and commercial units."""
    sq_meters: float = Field(..., description="Area in square meters (m²)")
    sq_kilometers: float = Field(..., description="Area in square kilometers (km²)")
    hectares: float = Field(..., description="Area in hectares (ha)")
    acres: float = Field(..., description="Area in international acres (ac)")
    sq_feet: float = Field(..., description="Area in square feet (ft²)")


class LengthUnits(BaseModel):
    """Length/distance measurements across standard units."""
    meters: float = Field(..., description="Length in meters (m)")
    kilometers: float = Field(..., description="Length in kilometers (km)")
    miles: float = Field(..., description="Length in miles (mi)")
    feet: float = Field(..., description="Length in feet (ft)")


class MeasurementDetails(BaseModel):
    """Measurement calculation results for an individual geometry."""
    supported: bool = Field(..., description="True if geometry supports geometric measurement calculation")
    geometry_type: str = Field(..., description="OGC geometry type")
    projected_crs: str = Field(..., description="Projected Coordinate Reference System used for planar measurement")
    projected_crs_name: Optional[str] = Field(None, description="Descriptive name of the projected CRS")
    
    # Area measurements (for Polygons / MultiPolygons)
    area: Optional[AreaUnits] = Field(None, description="Multi-unit area measurements")
    perimeter: Optional[LengthUnits] = Field(None, description="Multi-unit boundary perimeter measurements")
    
    # Length measurements (for LineStrings / MultiLineStrings)
    length: Optional[LengthUnits] = Field(None, description="Multi-unit length measurements")
    
    # Geodesic metrics (calculated on WGS84 ellipsoid without planar projection distortion)
    geodesic_area_sq_m: Optional[float] = Field(None, description="WGS84 ellipsoidal geodesic area in m²")
    geodesic_length_m: Optional[float] = Field(None, description="WGS84 ellipsoidal geodesic length in meters")
    
    # Graceful handling notes
    notes: Optional[str] = Field(None, description="Clarifying context or reason if measurement is not applicable")


class FeatureItem(BaseModel):
    """Processed geospatial feature containing identifiers, geometry, and measurements."""
    feature_id: Union[int, str] = Field(..., description="Unique feature index or identifier")
    geometry_type: str = Field(..., description="Type of geometry (e.g. Polygon, LineString, Point)")
    geometry: dict[str, Any] = Field(..., description="GeoJSON geometry representation")
    crs: str = Field(..., description="Source Coordinate Reference System (e.g. EPSG:4326)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Extracted feature attribute key-values")
    measurements: MeasurementDetails = Field(..., description="Calculated geometric measurements")
    centroid: Optional[list[float]] = Field(None, description="Centroid [longitude, latitude]")
    bbox: Optional[list[float]] = Field(None, description="Bounding box [minx, miny, maxx, maxy]")


class FileInfoResponse(BaseModel):
    """File metadata response complying with Assessment specification."""
    id: str = Field(..., description="Unique file identifier (e.g. abc123)")
    filename: str = Field(..., description="Original uploaded filename")
    feature_count: int = Field(..., description="Total count of geospatial features extracted")
    crs: str = Field(..., description="Detected source coordinate reference system")
    status: FileStatus = Field(..., description="Processing status (PENDING, PROCESSING, COMPLETED, FAILED)")
    
    # Extended metadata for UI and analytics
    file_size_bytes: Optional[int] = Field(None, description="Size of uploaded file in bytes")
    file_type: Optional[str] = Field(None, description="Detected format (shapefile or kml)")
    geometry_summary: Optional[dict[str, int]] = Field(default_factory=dict, description="Count per geometry type")
    projected_crs: Optional[str] = Field(None, description="Projected CRS selected for metric processing")
    created_at: Optional[str] = Field(None, description="ISO timestamp of upload")
    error_message: Optional[str] = Field(None, description="Error reason if status is FAILED")


class AggregateMeasurementSummary(BaseModel):
    """Aggregated measurements across all features in a file."""
    total_features: int
    measured_features: int
    unmeasured_features: int
    total_area_sq_m: float
    total_area_sq_km: float
    total_area_hectares: float
    total_area_acres: float
    total_length_m: float
    total_length_km: float
    total_length_miles: float
    geometry_breakdown: dict[str, int]


class MeasurementsSummaryResponse(BaseModel):
    """Measurements response endpoint returning feature-level and aggregate measurements."""
    file_id: str
    filename: str
    feature_count: int
    crs: str
    projected_crs_used: str
    summary: AggregateMeasurementSummary
    features: list[FeatureItem]


class FileListResponse(BaseModel):
    """Paginated list of uploaded files."""
    total: int
    files: list[FileInfoResponse]


class GeoJSONFeature(BaseModel):
    """Standard GeoJSON Feature."""
    type: str = "Feature"
    id: Union[int, str]
    geometry: dict[str, Any]
    properties: dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    """Standard GeoJSON FeatureCollection."""
    type: str = "FeatureCollection"
    name: Optional[str] = None
    crs: Optional[dict[str, Any]] = None
    features: list[GeoJSONFeature]
