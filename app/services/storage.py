"""File metadata and features persistence service."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from threading import Lock

from app.config import settings
from app.models.schemas import (
    FileInfoResponse,
    FileStatus,
    FeatureItem,
    AggregateMeasurementSummary,
    MeasurementsSummaryResponse,
)


class FileStorageService:
    """Manages metadata and processed feature items with in-memory caching and disk persistence."""

    def __init__(self):
        self._lock = Lock()
        self._files: Dict[str, FileInfoResponse] = {}
        self._features: Dict[str, List[FeatureItem]] = {}
        self._storage_dir: Path = settings.UPLOAD_DIR

        # Load existing state from disk on startup if any
        self._load_from_disk()

    def _meta_file_path(self, file_id: str) -> Path:
        return self._storage_dir / f"{file_id}.meta.json"

    def _features_file_path(self, file_id: str) -> Path:
        return self._storage_dir / f"{file_id}.features.json"

    def _load_from_disk(self):
        """Restores persisted metadata on server boot."""
        try:
            for meta_path in self._storage_dir.glob("*.meta.json"):
                file_id = meta_path.stem.replace(".meta", "")
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._files[file_id] = FileInfoResponse(**data)
                
                feat_path = self._features_file_path(file_id)
                if feat_path.exists():
                    with open(feat_path, "r", encoding="utf-8") as f:
                        f_data = json.load(f)
                        self._features[file_id] = [FeatureItem(**item) for item in f_data]
        except Exception:
            pass

    def create_file_record(self, filename: str, file_size_bytes: int, file_type: str) -> str:
        """Initializes a new file processing record and returns its unique ID."""
        file_id = uuid.uuid4().hex[:8]  # Clean 8-character hex id e.g. "a1b2c3d4"
        with self._lock:
            record = FileInfoResponse(
                id=file_id,
                filename=filename,
                file_size_bytes=file_size_bytes,
                file_type=file_type,
                feature_count=0,
                crs=settings.DEFAULT_CRS,
                status=FileStatus.PROCESSING,
                created_at=datetime.now(timezone.utc).isoformat(),
                geometry_summary={},
            )
            self._files[file_id] = record
            self._features[file_id] = []
            self._save_record_to_disk(file_id)
        return file_id

    def update_completed(
        self,
        file_id: str,
        features: List[FeatureItem],
        source_crs: str,
        projected_crs: str,
    ) -> FileInfoResponse:
        """Updates file record with successful processing results."""
        with self._lock:
            if file_id not in self._files:
                raise KeyError(f"File ID {file_id} not found.")

            # Compute summary breakdown
            geom_counts: dict[str, int] = {}
            tot_area_m2 = 0.0
            tot_len_m = 0.0

            for feat in features:
                g_type = feat.geometry_type
                geom_counts[g_type] = geom_counts.get(g_type, 0) + 1
                if feat.measurements.area:
                    tot_area_m2 += feat.measurements.area.sq_meters
                if feat.measurements.length:
                    tot_len_m += feat.measurements.length.meters

            record = self._files[file_id]
            updated_record = FileInfoResponse(
                id=record.id,
                filename=record.filename,
                file_size_bytes=record.file_size_bytes,
                file_type=record.file_type,
                feature_count=len(features),
                crs=source_crs,
                status=FileStatus.COMPLETED,
                created_at=record.created_at,
                geometry_summary=geom_counts,
                projected_crs=projected_crs,
                total_area_sq_m=round(tot_area_m2, 2) if tot_area_m2 > 0 else None,
                total_length_m=round(tot_len_m, 2) if tot_len_m > 0 else None,
            )

            self._files[file_id] = updated_record
            self._features[file_id] = features
            self._save_record_to_disk(file_id)
            self._save_features_to_disk(file_id)
            return updated_record

    def update_failed(self, file_id: str, error_message: str) -> FileInfoResponse:
        """Marks file record as failed with explanatory error message."""
        with self._lock:
            if file_id not in self._files:
                raise KeyError(f"File ID {file_id} not found.")

            record = self._files[file_id]
            updated_record = FileInfoResponse(
                id=record.id,
                filename=record.filename,
                file_size_bytes=record.file_size_bytes,
                file_type=record.file_type,
                feature_count=0,
                crs=record.crs,
                status=FileStatus.FAILED,
                created_at=record.created_at,
                error_message=error_message,
            )
            self._files[file_id] = updated_record
            self._save_record_to_disk(file_id)
            return updated_record

    def get_file(self, file_id: str) -> Optional[FileInfoResponse]:
        """Retrieves file metadata by ID."""
        with self._lock:
            return self._files.get(file_id)

    def get_features(
        self,
        file_id: str,
        geometry_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[FeatureItem]:
        """Retrieves features with optional filtering and pagination."""
        with self._lock:
            features = self._features.get(file_id, [])
            if geometry_type:
                features = [f for f in features if f.geometry_type.lower() == geometry_type.lower()]
            if offset:
                features = features[offset:]
            if limit:
                features = features[:limit]
            return features

    def get_measurements_summary(self, file_id: str) -> Optional[MeasurementsSummaryResponse]:
        """Builds full measurements summary response."""
        with self._lock:
            record = self._files.get(file_id)
            if not record:
                return None

            features = self._features.get(file_id, [])

            total_area_m2 = 0.0
            total_len_m = 0.0
            measured_count = 0
            unmeasured_count = 0
            breakdown: dict[str, int] = {}

            for feat in features:
                g_type = feat.geometry_type
                breakdown[g_type] = breakdown.get(g_type, 0) + 1

                if feat.measurements.supported:
                    measured_count += 1
                else:
                    unmeasured_count += 1

                if feat.measurements.area:
                    total_area_m2 += feat.measurements.area.sq_meters
                if feat.measurements.length:
                    total_len_m += feat.measurements.length.meters

            summary = AggregateMeasurementSummary(
                total_features=len(features),
                measured_features=measured_count,
                unmeasured_features=unmeasured_count,
                total_area_sq_m=round(total_area_m2, 3),
                total_area_sq_km=round(total_area_m2 * 1e-6, 6),
                total_area_hectares=round(total_area_m2 * 1e-4, 4),
                total_area_acres=round(total_area_m2 * 0.000247105, 4),
                total_length_m=round(total_len_m, 3),
                total_length_km=round(total_len_m * 1e-3, 4),
                total_length_miles=round(total_len_m * 0.000621371, 4),
                geometry_breakdown=breakdown,
            )

            return MeasurementsSummaryResponse(
                file_id=record.id,
                filename=record.filename,
                feature_count=record.feature_count,
                crs=record.crs,
                projected_crs_used=record.projected_crs or "N/A",
                summary=summary,
                features=features,
            )

    def list_files(self) -> List[FileInfoResponse]:
        """Lists all uploaded files sorted newest first."""
        with self._lock:
            records = list(self._files.values())
            records.sort(key=lambda r: r.created_at or "", reverse=True)
            return records

    def delete_file(self, file_id: str) -> bool:
        """Removes a file and associated artifacts."""
        with self._lock:
            if file_id in self._files:
                del self._files[file_id]
                if file_id in self._features:
                    del self._features[file_id]

                # Delete disk artifacts
                meta = self._meta_file_path(file_id)
                feat = self._features_file_path(file_id)
                if meta.exists():
                    meta.unlink(missing_ok=True)
                if feat.exists():
                    feat.unlink(missing_ok=True)
                return True
            return False

    def _save_record_to_disk(self, file_id: str):
        record = self._files.get(file_id)
        if record:
            path = self._meta_file_path(file_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record.model_dump(), f, indent=2)

    def _save_features_to_disk(self, file_id: str):
        features = self._features.get(file_id)
        if features is not None:
            path = self._features_file_path(file_id)
            with open(path, "w", encoding="utf-8") as f:
                json.dump([feat.model_dump() for feat in features], f)


storage_service = FileStorageService()
