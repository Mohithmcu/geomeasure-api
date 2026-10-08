"""Unit tests for measurement calculations across geometry types."""

import pytest
import pyproj
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from app.services.measurement_service import measurement_service


def test_polygon_area_and_perimeter():
    """Test calculation of area and perimeter for a known square polygon in Paris (lat 48.85, lon 2.35)."""
    # 0.01 deg lat is ~1,112 meters; 0.01 deg lon at lat 48.85 is ~732 meters
    # Square ~ 732m x 1112m -> Area ~ 814,000 m²
    poly = Polygon([
        (2.35, 48.85),
        (2.36, 48.85),
        (2.36, 48.86),
        (2.35, 48.86),
        (2.35, 48.85)
    ])
    wgs84 = pyproj.CRS.from_epsg(4326)

    meas, _, _, proj_epsg = measurement_service.compute_measurements(poly, wgs84)

    assert meas.supported is True
    assert meas.geometry_type == "Polygon"
    assert meas.projected_crs == "EPSG:32631"  # Paris is in UTM Zone 31N
    assert meas.area is not None
    assert 700000 < meas.area.sq_meters < 900000
    assert meas.area.hectares > 70
    assert meas.area.acres > 150
    assert meas.perimeter is not None
    assert meas.perimeter.meters > 3000
    assert meas.geodesic_area_sq_m is not None


def test_linestring_length():
    """Test calculation of length for a LineString in meters and kilometers."""
    # Line ~ 1 km long
    line = LineString([(0.0, 51.5), (0.01, 51.5)])
    wgs84 = pyproj.CRS.from_epsg(4326)

    meas, _, _, proj_epsg = measurement_service.compute_measurements(line, wgs84)

    assert meas.supported is True
    assert meas.geometry_type == "LineString"
    assert meas.length is not None
    assert 600 < meas.length.meters < 800  # ~690 meters at 51.5 deg lat
    assert meas.area is None
    assert meas.perimeter is None
    assert meas.geodesic_length_m is not None


def test_point_graceful_handling():
    """Requirement: Point: No measurement is required. API handles gracefully rather than crashing."""
    pt = Point(77.5946, 12.9716)
    wgs84 = pyproj.CRS.from_epsg(4326)

    meas, _, _, proj_epsg = measurement_service.compute_measurements(pt, wgs84)

    assert meas.supported is False
    assert meas.geometry_type == "Point"
    assert meas.area is None
    assert meas.length is None
    assert meas.perimeter is None
    assert "Point" in meas.notes
