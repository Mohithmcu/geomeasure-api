"""CRS (Coordinate Reference System) detection, transformation, and UTM zone selection service."""

import math
from typing import Optional, Tuple
import pyproj
from shapely.geometry.base import BaseGeometry


class CRSService:
    """Manages Coordinate Reference Systems, projections, and transformation pipelines."""

    def __init__(self):
        self.wgs84_crs = pyproj.CRS.from_epsg(4326)
        self.geod = pyproj.Geod(ellps="WGS84")

    @staticmethod
    def parse_crs(crs_input: Optional[str]) -> Tuple[pyproj.CRS, str]:
        """Parse CRS from PRJ WKT, EPSG string, or authority code.
        
        Returns:
            Tuple of (pyproj.CRS object, normalized CRS string e.g. 'EPSG:4326')
        """
        if not crs_input or not crs_input.strip():
            return pyproj.CRS.from_epsg(4326), "EPSG:4326"

        text = crs_input.strip()

        try:
            # Check if integer string e.g. "4326"
            if text.isdigit():
                crs = pyproj.CRS.from_epsg(int(text))
                return crs, f"EPSG:{text}"

            # Check if authority format e.g. "EPSG:4326"
            if text.upper().startswith("EPSG:"):
                crs = pyproj.CRS.from_user_input(text)
                return crs, text.upper()

            # Attempt parsing as WKT or proj string
            crs = pyproj.CRS.from_user_input(text)
            epsg = crs.to_epsg()
            if epsg:
                return crs, f"EPSG:{epsg}"
            return crs, crs.name or "CUSTOM_PROJECTED"
        except Exception:
            # Fallback to WGS84 if unrecognizable
            return pyproj.CRS.from_epsg(4326), "EPSG:4326"

    @staticmethod
    def is_geographic(crs: pyproj.CRS) -> bool:
        """Check whether CRS uses angular/geographic units (e.g. degrees) rather than meters."""
        return crs.is_geographic

    @staticmethod
    def determine_optimal_projected_crs(lon: float, lat: float) -> Tuple[pyproj.CRS, str, str]:
        """Dynamically determines the best projected CRS for a given geographic location.
        
        Strategy:
        1. Universal Transverse Mercator (UTM) provides low scale distortion (<0.1%)
           for conformal planar mapping within each 6-degree longitudinal zone.
        2. Northern hemisphere uses EPSG:32601 - 32660.
        3. Southern hemisphere uses EPSG:32701 - 32760.
        4. Polar latitudes (|lat| > 84°) transition to Universal Polar Stereographic (UPS):
           - North: EPSG:3413 (WGS 84 / NSIDC Sea Ice Polar Stereographic North)
           - South: EPSG:3031 (WGS 84 / Antarctic Polar Stereographic)
        
        Returns:
            Tuple of (pyproj.CRS, epsg_code_string, descriptive_name)
        """
        # Clamp latitude to valid ranges
        lat = max(-90.0, min(90.0, lat))
        # Normalize longitude between -180 and 180
        lon = (lon + 180.0) % 360.0 - 180.0

        # Handle Polar regions
        if lat > 84.0:
            crs = pyproj.CRS.from_epsg(3413)
            return crs, "EPSG:3413", "WGS 84 / NSIDC Polar Stereographic North"
        if lat < -80.0:
            crs = pyproj.CRS.from_epsg(3031)
            return crs, "EPSG:3031", "WGS 84 / Antarctic Polar Stereographic"

        # Calculate UTM zone (1 to 60)
        zone = int(math.floor((lon + 180.0) / 6.0)) + 1
        zone = max(1, min(60, zone))

        if lat >= 0:
            epsg_code = 32600 + zone
            hemisphere = "N"
        else:
            epsg_code = 32700 + zone
            hemisphere = "S"

        crs = pyproj.CRS.from_epsg(epsg_code)
        name = f"WGS 84 / UTM zone {zone}{hemisphere}"
        return crs, f"EPSG:{epsg_code}", name

    def get_transformer(self, source_crs: pyproj.CRS, target_crs: pyproj.CRS) -> pyproj.Transformer:
        """Create a thread-safe coordinate transformer with always_xy=True."""
        return pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)

    @staticmethod
    def transform_geometry(geom: BaseGeometry, transformer: pyproj.Transformer) -> BaseGeometry:
        """Applies coordinate transformation to geometry using modern vectorized Shapely 2.x API."""
        import numpy as np
        import shapely

        def _transform_coords(coords):
            x, y = transformer.transform(coords[:, 0], coords[:, 1])
            return np.column_stack((x, y))

        return shapely.transform(geom, _transform_coords)

    def to_wgs84(self, geom: BaseGeometry, source_crs: pyproj.CRS) -> BaseGeometry:
        """Reprojects any geometry to WGS84 (EPSG:4326) for GeoJSON output and map display."""
        if source_crs.to_epsg() == 4326:
            return geom
        transformer = self.get_transformer(source_crs, self.wgs84_crs)
        return self.transform_geometry(geom, transformer)


# Global singleton instance
crs_service = CRSService()
