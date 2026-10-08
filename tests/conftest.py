"""Test suite configuration and fixtures."""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

TESTS_DIR = Path(__file__).parent
BASE_DIR = TESTS_DIR.parent


@pytest.fixture(scope="session")
def client():
    """FastAPI test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def sample_parcels_zip():
    """Path to sample shapefile zip."""
    return BASE_DIR / "samples" / "sample_land_parcels.zip"


@pytest.fixture(scope="session")
def sample_pipelines_kml():
    """Path to sample utility pipeline KML."""
    return BASE_DIR / "samples" / "sample_utility_network.kml"


@pytest.fixture(scope="session")
def sample_points_kml():
    """Path to sample points KML."""
    return BASE_DIR / "samples" / "sample_points_of_interest.kml"
