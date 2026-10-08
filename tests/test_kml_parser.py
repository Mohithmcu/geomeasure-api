"""Unit tests for KML parser."""

import pytest
from app.services.kml_parser import kml_parser


def test_parse_sample_pipelines(sample_pipelines_kml):
    """Test parsing the sample utility network KML with mixed geometries."""
    assert sample_pipelines_kml.exists()

    features, source_crs, proj_crs = kml_parser.parse_file(sample_pipelines_kml)

    # 2 LineStrings, 1 Polygon, 1 Point
    assert len(features) == 4
    assert source_crs == "EPSG:4326"

    geom_types = [f.geometry_type for f in features]
    assert "LineString" in geom_types
    assert "Polygon" in geom_types
    assert "Point" in geom_types

    # Find the gas main line
    gas_lines = [f for f in features if f.properties.get("name") == "North Gas Transmission Main"]
    assert len(gas_lines) == 1
    gas_line = gas_lines[0]
    assert gas_line.measurements.length is not None
    assert gas_line.measurements.length.meters > 1000
    assert gas_line.properties.get("Material") == "API 5L X65 Steel"


def test_parse_sample_points(sample_points_kml):
    """Test parsing benchmark points and verifying graceful handling."""
    assert sample_points_kml.exists()

    features, source_crs, proj_crs = kml_parser.parse_file(sample_points_kml)

    assert len(features) == 3
    for feat in features:
        assert feat.geometry_type == "Point"
        assert feat.measurements.supported is False
        assert feat.measurements.area is None
        assert feat.measurements.length is None
