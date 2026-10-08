"""Unit tests for Coordinate Reference System (CRS) management and UTM projection selection."""

import pytest
from app.services.crs_service import crs_service


def test_parse_crs_epsg_code():
    crs, code = crs_service.parse_crs("EPSG:4326")
    assert code == "EPSG:4326"
    assert crs.to_epsg() == 4326
    assert crs_service.is_geographic(crs) is True


def test_parse_crs_integer_string():
    crs, code = crs_service.parse_crs("3857")
    assert code == "EPSG:3857"
    assert crs.to_epsg() == 3857
    assert crs_service.is_geographic(crs) is False


def test_parse_crs_fallback():
    crs, code = crs_service.parse_crs(None)
    assert code == "EPSG:4326"
    assert crs.to_epsg() == 4326


def test_determine_optimal_utm_northern_hemisphere():
    # Fresno, California: Lon -119.78, Lat 36.74 -> Zone 11N (EPSG:32611)
    crs, epsg, name = crs_service.determine_optimal_projected_crs(-119.78, 36.74)
    assert epsg == "EPSG:32611"
    assert "UTM zone 11N" in name
    assert crs_service.is_geographic(crs) is False


def test_determine_optimal_utm_southern_hemisphere():
    # Sydney, Australia: Lon 151.20, Lat -33.86 -> Zone 56S (EPSG:32756)
    crs, epsg, name = crs_service.determine_optimal_projected_crs(151.20, -33.86)
    assert epsg == "EPSG:32756"
    assert "UTM zone 56S" in name


def test_determine_optimal_polar_regions():
    # North Pole (>84 deg N) -> EPSG:3413
    crs, epsg, name = crs_service.determine_optimal_projected_crs(0.0, 88.0)
    assert epsg == "EPSG:3413"

    # South Pole (<-80 deg S) -> EPSG:3031
    crs, epsg, name = crs_service.determine_optimal_projected_crs(0.0, -85.0)
    assert epsg == "EPSG:3031"
