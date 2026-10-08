"""Shapefile (.zip) parser and feature extraction service."""

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, List, Tuple
import shapefile
from shapely.geometry import shape, mapping

from app.models.schemas import FeatureItem
from app.services.crs_service import crs_service
from app.services.measurement_service import measurement_service


class ShapefileParser:
    """Extracts, validates, and processes ESRI Shapefiles from zip archives."""

    def __init__(self):
        self.crs_service = crs_service
        self.measurement_service = measurement_service

    def extract_and_parse(self, zip_path: Path) -> Tuple[List[FeatureItem], str, str]:
        """Extracts zipped shapefile, detects CRS, and computes measurements for all features.
        
        Args:
            zip_path: Path to the uploaded .zip archive
            
        Returns:
            Tuple of:
                - List of FeatureItem objects
                - Detected source CRS string (e.g. 'EPSG:4326')
                - Projected CRS string used
        """
        temp_dir = tempfile.mkdtemp(prefix="shp_extract_")
        try:
            # 1. Safely extract zip archive preventing Zip Slip
            with zipfile.ZipFile(zip_path, "r") as zf:
                for member in zf.infolist():
                    target_path = Path(temp_dir) / member.filename
                    # Resolve real path to ensure it remains inside temp_dir
                    target_path_resolved = target_path.resolve()
                    if not str(target_path_resolved).startswith(str(Path(temp_dir).resolve())):
                        raise ValueError(f"Malicious zip path detected: {member.filename}")
                zf.extractall(temp_dir)

            # 2. Locate .shp file within extracted tree
            shp_files = list(Path(temp_dir).rglob("*.shp"))
            if not shp_files:
                raise ValueError("No .shp file found inside the provided zip archive.")

            primary_shp = shp_files[0]
            base_stem = primary_shp.stem
            parent_dir = primary_shp.parent

            # 3. Detect CRS from companion .prj file
            prj_files = list(parent_dir.glob(f"{base_stem}.prj"))
            if not prj_files:
                # Check case-insensitive
                prj_files = [p for p in parent_dir.glob("*.prj") if p.stem.lower() == base_stem.lower()]

            source_crs_str = "EPSG:4326"
            if prj_files and prj_files[0].exists():
                try:
                    prj_content = prj_files[0].read_text(encoding="utf-8", errors="ignore").strip()
                    source_crs, source_crs_str = self.crs_service.parse_crs(prj_content)
                except Exception:
                    source_crs, source_crs_str = self.crs_service.parse_crs("EPSG:4326")
            else:
                source_crs, source_crs_str = self.crs_service.parse_crs("EPSG:4326")

            # 4. Open shapefile with PyShp (trying utf-8, then latin1 fallback)
            reader = None
            for enc in ("utf-8", "latin-1", "cp1252"):
                try:
                    reader = shapefile.Reader(str(primary_shp), encoding=enc)
                    # Test reading first record
                    if len(reader) > 0:
                        _ = reader.record(0)
                    break
                except Exception:
                    continue

            if reader is None:
                reader = shapefile.Reader(str(primary_shp))

            field_names = [f[0] for f in reader.fields[1:]]  # Skip deletion flag field

            features: List[FeatureItem] = []
            projected_crs_used = source_crs_str

            for idx, shape_rec in enumerate(reader.shapeRecords(), start=1):
                raw_shape = shape_rec.shape
                record = shape_rec.record

                # Build clean attributes dictionary
                properties: dict[str, Any] = {}
                for f_name, f_val in zip(field_names, record):
                    if hasattr(f_val, "isoformat"):
                        properties[f_name] = f_val.isoformat()
                    elif isinstance(f_val, bytes):
                        properties[f_name] = f_val.decode("utf-8", errors="replace")
                    else:
                        properties[f_name] = f_val

                # Skip completely null geometries safely
                if not raw_shape.points and raw_shape.shapeType == shapefile.NULL:
                    continue

                # Convert to Shapely geometry via __geo_interface__
                try:
                    geom = shape(raw_shape.__geo_interface__)
                except Exception as e:
                    # Graceful recovery for unparseable shapes
                    continue

                # Compute measurements with automated CRS projection
                meas_details, wgs84_geom, _, proj_epsg = self.measurement_service.compute_measurements(
                    geom, source_crs, fallback_source_crs_name=source_crs_str
                )
                projected_crs_used = proj_epsg

                # Feature ID from properties or 1-based index
                feature_id = properties.get("FID") or properties.get("id") or properties.get("ID") or idx

                centroid_coords = None
                bbox_coords = None
                if not wgs84_geom.is_empty:
                    centroid = wgs84_geom.centroid
                    centroid_coords = [round(centroid.x, 6), round(centroid.y, 6)]
                    bbox_coords = [round(c, 6) for c in wgs84_geom.bounds]

                features.append(
                    FeatureItem(
                        feature_id=feature_id,
                        geometry_type=geom.geom_type,
                        geometry=mapping(wgs84_geom),
                        crs=source_crs_str,
                        properties=properties,
                        measurements=meas_details,
                        centroid=centroid_coords,
                        bbox=bbox_coords,
                    )
                )

            return features, source_crs_str, projected_crs_used

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


shapefile_parser = ShapefileParser()
