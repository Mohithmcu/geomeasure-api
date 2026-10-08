"""Orchestrator for geospatial file processing pipelines."""

from pathlib import Path
from typing import Tuple

from app.models.schemas import FileInfoResponse, FileStatus
from app.services.shapefile_parser import shapefile_parser
from app.services.kml_parser import kml_parser
from app.services.storage import storage_service


class GeospatialProcessor:
    """Coordinates parsing, projection transformation, measurement computation, and persistence."""

    def __init__(self):
        self.storage = storage_service
        self.shapefile_parser = shapefile_parser
        self.kml_parser = kml_parser

    def process_file(self, file_id: str, file_path: Path, filename: str) -> FileInfoResponse:
        """Processes an uploaded geospatial file synchronously or within background task.
        
        Args:
            file_id: Pre-allocated identifier
            file_path: Saved location of the uploaded file on disk
            filename: Original name of the uploaded file
            
        Returns:
            FileInfoResponse: Updated metadata with COMPLETED or FAILED status
        """
        suffix = file_path.suffix.lower()

        try:
            if suffix == ".zip":
                features, source_crs, proj_crs = self.shapefile_parser.extract_and_parse(file_path)
            elif suffix in (".kml", ".kmz"):
                features, source_crs, proj_crs = self.kml_parser.parse_file(file_path)
            else:
                raise ValueError(f"Unsupported file format '{suffix}'. Supported: .zip (Shapefile), .kml, .kmz")

            # Update storage record
            updated_info = self.storage.update_completed(
                file_id=file_id,
                features=features,
                source_crs=source_crs,
                projected_crs=proj_crs,
            )
            return updated_info

        except Exception as exc:
            # Handle failures gracefully with informative description
            error_msg = f"Processing error: {str(exc)}"
            return self.storage.update_failed(file_id, error_msg)


processor = GeospatialProcessor()
