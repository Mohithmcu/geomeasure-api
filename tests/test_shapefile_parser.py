"""Unit tests for Shapefile extraction and parsing service."""

import pytest
from app.services.shapefile_parser import shapefile_parser


def test_parse_sample_parcels(sample_parcels_zip):
    """Test extracting and parsing the sample agricultural parcels shapefile."""
    assert sample_parcels_zip.exists(), "Sample shapefile zip must exist."

    features, source_crs, proj_crs = shapefile_parser.extract_and_parse(sample_parcels_zip)

    assert len(features) == 4
    assert source_crs == "EPSG:4326"
    assert proj_crs == "EPSG:32611"  # California UTM Zone 11N

    for feat in features:
        assert feat.geometry_type == "Polygon"
        assert feat.measurements.supported is True
        assert feat.measurements.area is not None
        assert feat.measurements.area.sq_meters > 0
        assert "PARCEL_ID" in feat.properties
        assert "LAND_USE" in feat.properties
