"""Measurement calculation service for geospatial geometries.

Transforms geometries to optimal projected CRS before computing linear and areal measurements.
Converts results to standard scientific and engineering units.
Computes geodesic reference metrics on the WGS84 ellipsoid.
"""

from typing import Tuple, Optional
import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform
from shapely.validation import make_valid

from app.models.schemas import (
    AreaUnits,
    LengthUnits,
    MeasurementDetails,
)
from app.services.crs_service import crs_service


class MeasurementService:
    """Computes rigorous metric measurements for geospatial geometries."""

    # Unit conversion constants
    SQ_METERS_TO_SQ_KM = 1e-6
    SQ_METERS_TO_HECTARES = 1e-4
    SQ_METERS_TO_ACRES = 0.00024710538146717
    SQ_METERS_TO_SQ_FEET = 10.763910416709722

    METERS_TO_KM = 1e-3
    METERS_TO_MILES = 0.00062137119223733
    METERS_TO_FEET = 3.280839895013123

    def __init__(self):
        self.crs_service = crs_service

    def build_area_units(self, area_sq_m: float) -> AreaUnits:
        """Construct multi-unit area object from square meters."""
        area_sq_m = max(0.0, float(area_sq_m))
        return AreaUnits(
            sq_meters=round(area_sq_m, 3),
            sq_kilometers=round(area_sq_m * self.SQ_METERS_TO_SQ_KM, 6),
            hectares=round(area_sq_m * self.SQ_METERS_TO_HECTARES, 4),
            acres=round(area_sq_m * self.SQ_METERS_TO_ACRES, 4),
            sq_feet=round(area_sq_m * self.SQ_METERS_TO_SQ_FEET, 2),
        )

    def build_length_units(self, length_m: float) -> LengthUnits:
        """Construct multi-unit length object from meters."""
        length_m = max(0.0, float(length_m))
        return LengthUnits(
            meters=round(length_m, 3),
            kilometers=round(length_m * self.METERS_TO_KM, 4),
            miles=round(length_m * self.METERS_TO_MILES, 4),
            feet=round(length_m * self.METERS_TO_FEET, 2),
        )

    def compute_measurements(
        self,
        geom: BaseGeometry,
        source_crs: pyproj.CRS,
        fallback_source_crs_name: str = "EPSG:4326"
    ) -> Tuple[MeasurementDetails, BaseGeometry, pyproj.CRS, str]:
        """Calculates measurements for a geometry with automatic CRS reprojection.
        
        Args:
            geom: Shapely geometry object
            source_crs: Detected or assigned source CRS
            fallback_source_crs_name: String representation of source CRS
            
        Returns:
            Tuple of:
                - MeasurementDetails object
                - Geometry reprojected to WGS84 (for GeoJSON / Leaflet mapping)
                - Projected CRS object used for planar measurement
                - Projected CRS string (e.g. 'EPSG:32643')
        """
        geom_type = geom.geom_type

        # Ensure valid geometry topology
        if not geom.is_valid:
            try:
                geom = make_valid(geom)
            except Exception:
                pass

        # Convert to WGS84 for location centroid and geodesic calculation
        wgs84_geom = self.crs_service.to_wgs84(geom, source_crs)

        # Handle empty geometries gracefully
        if geom.is_empty:
            return (
                MeasurementDetails(
                    supported=False,
                    geometry_type=geom_type,
                    projected_crs="N/A",
                    notes="Empty geometry; no coordinates available.",
                ),
                wgs84_geom,
                source_crs,
                "N/A",
            )

        # Identify centroid coordinates to pick the most accurate projected system
        centroid = wgs84_geom.centroid
        centroid_lon = centroid.x
        centroid_lat = centroid.y

        # Determine target projected CRS
        if self.crs_service.is_geographic(source_crs):
            proj_crs, proj_epsg, proj_name = self.crs_service.determine_optimal_projected_crs(
                centroid_lon, centroid_lat
            )
            transformer = self.crs_service.get_transformer(source_crs, proj_crs)
            projected_geom = self.crs_service.transform_geometry(geom, transformer)
        else:
            # Source is already projected (e.g. UTM, State Plane, BNG)
            proj_crs = source_crs
            proj_epsg = source_crs.to_epsg()
            proj_epsg = f"EPSG:{proj_epsg}" if proj_epsg else (source_crs.name or "PROJECTED")
            proj_name = source_crs.name or "Source Projected CRS"
            projected_geom = geom

        # Process by geometry type
        if geom_type in ("Polygon", "MultiPolygon"):
            # Area in square meters (planar)
            area_sq_m = projected_geom.area
            # Perimeter in meters (planar boundary length)
            perimeter_m = projected_geom.length

            # Ellipsoidal geodesic calculation
            try:
                geodesic_area, geodesic_perim = self.crs_service.geod.geometry_area_perimeter(wgs84_geom)
                geodesic_area_sq_m = round(abs(geodesic_area), 3)
            except Exception:
                geodesic_area_sq_m = None

            details = MeasurementDetails(
                supported=True,
                geometry_type=geom_type,
                projected_crs=proj_epsg,
                projected_crs_name=proj_name,
                area=self.build_area_units(area_sq_m),
                perimeter=self.build_length_units(perimeter_m),
                geodesic_area_sq_m=geodesic_area_sq_m,
                notes="Measurements calculated in projected metric CRS. Geodesic area computed on WGS84 ellipsoid.",
            )
            return details, wgs84_geom, proj_crs, proj_epsg

        elif geom_type in ("LineString", "MultiLineString"):
            # Length in meters (planar)
            length_m = projected_geom.length

            # Ellipsoidal geodesic calculation
            try:
                geodesic_length = self.crs_service.geod.geometry_length(wgs84_geom)
                geodesic_length_m = round(abs(geodesic_length), 3)
            except Exception:
                geodesic_length_m = None

            details = MeasurementDetails(
                supported=True,
                geometry_type=geom_type,
                projected_crs=proj_epsg,
                projected_crs_name=proj_name,
                length=self.build_length_units(length_m),
                geodesic_length_m=geodesic_length_m,
                notes="Length calculated in projected metric CRS. Geodesic length computed on WGS84 ellipsoid.",
            )
            return details, wgs84_geom, proj_crs, proj_epsg

        elif geom_type in ("Point", "MultiPoint"):
            details = MeasurementDetails(
                supported=False,
                geometry_type=geom_type,
                projected_crs=proj_epsg,
                projected_crs_name=proj_name,
                notes="Point features represent 0-dimensional coordinates. Measurement not applicable.",
            )
            return details, wgs84_geom, proj_crs, proj_epsg

        elif geom_type == "GeometryCollection":
            # Graceful handling for geometry collections
            # Calculate sum of polygon areas and line lengths
            total_area = sum(g.area for g in projected_geom.geoms if g.geom_type in ("Polygon", "MultiPolygon"))
            total_len = sum(g.length for g in projected_geom.geoms if g.geom_type in ("LineString", "MultiLineString"))
            
            has_area = any(g.geom_type in ("Polygon", "MultiPolygon") for g in projected_geom.geoms)
            has_len = any(g.geom_type in ("LineString", "MultiLineString") for g in projected_geom.geoms)

            details = MeasurementDetails(
                supported=has_area or has_len,
                geometry_type=geom_type,
                projected_crs=proj_epsg,
                projected_crs_name=proj_name,
                area=self.build_area_units(total_area) if has_area else None,
                length=self.build_length_units(total_len) if has_len else None,
                notes="GeometryCollection: aggregate measurements computed from constituent elements.",
            )
            return details, wgs84_geom, proj_crs, proj_epsg

        else:
            # Graceful fallback for any unfamiliar geometry type
            details = MeasurementDetails(
                supported=False,
                geometry_type=geom_type,
                projected_crs=proj_epsg,
                projected_crs_name=proj_name,
                notes=f"Geometry type '{geom_type}' is not supported for measurement calculation.",
            )
            return details, wgs84_geom, proj_crs, proj_epsg


# Global singleton instance
measurement_service = MeasurementService()
