"""Integration tests for FastAPI endpoints."""

import io
import pytest


def test_health_check(client):
    """Test health diagnostic endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "geospatial_libraries" in data
    assert "shapely" in data["geospatial_libraries"]


def test_upload_shapefile_and_get_measurements(client, sample_parcels_zip):
    """Test uploading a zipped Shapefile and querying metadata and measurements."""
    with open(sample_parcels_zip, "rb") as f:
        file_bytes = f.read()

    # 1. Upload Shapefile
    upload_res = client.post(
        "/api/files/",
        files={"file": ("sample_land_parcels.zip", file_bytes, "application/zip")},
    )
    assert upload_res.status_code == 201
    file_info = upload_res.json()
    file_id = file_info["id"]

    assert file_info["filename"] == "sample_land_parcels.zip"
    assert file_info["feature_count"] == 4
    assert file_info["status"] == "COMPLETED"
    assert file_info["crs"] == "EPSG:4326"

    # 2. Query File Metadata via GET /api/files/{id}/
    info_res = client.get(f"/api/files/{file_id}/")
    assert info_res.status_code == 200
    assert info_res.json()["id"] == file_id

    # 3. Query Measurements via GET /api/files/{id}/measurements/
    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    meas_data = meas_res.json()

    assert meas_data["file_id"] == file_id
    assert meas_data["feature_count"] == 4
    assert len(meas_data["features"]) == 4
    assert meas_data["summary"]["total_area_sq_m"] > 0
    assert meas_data["summary"]["geometry_breakdown"]["Polygon"] == 4

    # 4. Query GeoJSON representation
    geo_res = client.get(f"/api/files/{file_id}/geojson/")
    assert geo_res.status_code == 200
    geo_data = geo_res.json()
    assert geo_data["type"] == "FeatureCollection"
    assert len(geo_data["features"]) == 4

    # 5. Delete file
    del_res = client.delete(f"/api/files/{file_id}/")
    assert del_res.status_code == 200

    # 6. Verify 404 after deletion
    assert client.get(f"/api/files/{file_id}/").status_code == 404


def test_upload_kml_and_filtering(client, sample_pipelines_kml):
    """Test uploading a KML file and testing geometry filtering on measurements."""
    with open(sample_pipelines_kml, "rb") as f:
        file_bytes = f.read()

    upload_res = client.post(
        "/api/files/",
        files={"file": ("sample_utility_network.kml", file_bytes, "application/vnd.google-earth.kml+xml")},
    )
    assert upload_res.status_code == 201
    file_info = upload_res.json()
    file_id = file_info["id"]

    # Filter by geometry_type=LineString
    line_res = client.get(f"/api/files/{file_id}/measurements/?geometry_type=LineString")
    assert line_res.status_code == 200
    line_data = line_res.json()
    for feat in line_data["features"]:
        assert feat["geometry_type"] == "LineString"
        assert feat["measurements"]["length"] is not None

    # Filter by geometry_type=Point
    pt_res = client.get(f"/api/files/{file_id}/measurements/?geometry_type=Point")
    assert pt_res.status_code == 200
    pt_data = pt_res.json()
    assert len(pt_data["features"]) == 1
    assert pt_data["features"][0]["measurements"]["supported"] is False


def test_upload_invalid_file_format(client):
    """Test rejecting unsupported file extensions with 400."""
    fake_txt = io.BytesIO(b"Hello world")
    response = client.post(
        "/api/files/",
        files={"file": ("unsupported.txt", fake_txt, "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_get_nonexistent_file(client):
    """Test 404 when file ID is not found."""
    response = client.get("/api/files/nonexistent_id/")
    assert response.status_code == 404
