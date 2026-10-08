"""KML and KMZ file parser and feature extraction service."""

import re
import zipfile
from pathlib import Path
from typing import Any, List, Optional, Tuple
import xml.etree.ElementTree as ET
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, MultiLineString, mapping
from shapely.geometry.base import BaseGeometry

from app.models.schemas import FeatureItem
from app.services.crs_service import crs_service
from app.services.measurement_service import measurement_service


class KMLParser:
    """Parses OGC KML (and KMZ) files, extracts Placemarks and geometries, and computes measurements."""

    def __init__(self):
        self.crs_service = crs_service
        self.measurement_service = measurement_service

    def _parse_coordinates_text(self, text: Optional[str]) -> List[Tuple[float, float]]:
        """Parses KML coordinate string e.g. 'lon,lat,alt lon,lat,alt' into [(lon, lat), ...]."""
        if not text:
            return []
        
        coords: List[Tuple[float, float]] = []
        # Split by whitespace or newlines
        tokens = re.split(r"\s+", text.strip())
        for token in tokens:
            if not token:
                continue
            parts = token.split(",")
            if len(parts) >= 2:
                try:
                    lon = float(parts[0].strip())
                    lat = float(parts[1].strip())
                    coords.append((lon, lat))
                except ValueError:
                    continue
        return coords

    def _parse_geometry_element(self, elem: ET.Element) -> Optional[BaseGeometry]:
        """Extracts Shapely geometry from an XML element (Polygon, LineString, Point, MultiGeometry)."""
        tag = elem.tag.split("}")[-1]  # Strip XML namespace

        if tag == "Point":
            coords_elem = elem.find(".//{*}coordinates")
            if coords_elem is not None and coords_elem.text:
                coords = self._parse_coordinates_text(coords_elem.text)
                if coords:
                    return Point(coords[0])
            return None

        elif tag == "LineString":
            coords_elem = elem.find(".//{*}coordinates")
            if coords_elem is not None and coords_elem.text:
                coords = self._parse_coordinates_text(coords_elem.text)
                if len(coords) >= 2:
                    return LineString(coords)
            return None

        elif tag == "Polygon":
            # Outer ring
            outer_elem = elem.find(".//{*}outerBoundaryIs//{*}coordinates")
            if outer_elem is None or not outer_elem.text:
                return None
            outer_coords = self._parse_coordinates_text(outer_elem.text)
            if len(outer_coords) < 3:
                return None
            
            # Ensure closed ring
            if outer_coords[0] != outer_coords[-1]:
                outer_coords.append(outer_coords[0])

            # Inner rings (holes)
            inner_rings: List[List[Tuple[float, float]]] = []
            for inner_elem in elem.findall(".//{*}innerBoundaryIs//{*}coordinates"):
                if inner_elem.text:
                    hole_coords = self._parse_coordinates_text(inner_elem.text)
                    if len(hole_coords) >= 3:
                        if hole_coords[0] != hole_coords[-1]:
                            hole_coords.append(hole_coords[0])
                        inner_rings.append(hole_coords)

            return Polygon(outer_coords, inner_rings)

        elif tag == "MultiGeometry":
            sub_geoms: List[BaseGeometry] = []
            for child in elem:
                sub_g = self._parse_geometry_element(child)
                if sub_g:
                    sub_geoms.append(sub_g)

            if not sub_geoms:
                return None

            # Check if all sub_geoms are Polygons
            if all(isinstance(g, Polygon) for g in sub_geoms):
                return MultiPolygon(sub_geoms)
            # Check if all are LineStrings
            if all(isinstance(g, LineString) for g in sub_geoms):
                return MultiLineString(sub_geoms)
            
            # Return first geometry or generic collection
            return sub_geoms[0]

        return None

    def _extract_placemark_properties(self, pm_elem: ET.Element) -> dict[str, Any]:
        """Extracts attributes, metadata, and ExtendedData from a Placemark element."""
        props: dict[str, Any] = {}

        name_elem = pm_elem.find(".//{*}name")
        if name_elem is not None and name_elem.text:
            props["name"] = name_elem.text.strip()

        desc_elem = pm_elem.find(".//{*}description")
        if desc_elem is not None and desc_elem.text:
            props["description"] = desc_elem.text.strip()

        # Parse <ExtendedData> -> <Data name="..."> <value>...</value> </Data>
        for data_elem in pm_elem.findall(".//{*}ExtendedData//{*}Data"):
            key = data_elem.attrib.get("name")
            val_elem = data_elem.find(".//{*}value")
            if key and val_elem is not None and val_elem.text:
                props[key] = val_elem.text.strip()

        # Parse <SchemaData> -> <SimpleData name="...">...</SimpleData>
        for simple_elem in pm_elem.findall(".//{*}SchemaData//{*}SimpleData"):
            key = simple_elem.attrib.get("name")
            if key and simple_elem.text:
                props[key] = simple_elem.text.strip()

        return props

    def parse_kml_content(self, kml_text: str) -> Tuple[List[FeatureItem], str, str]:
        """Parses KML XML string, extracts all features, and computes metric measurements."""
        root = ET.fromstring(kml_text)
        placemarks = root.findall(".//{*}Placemark")

        source_crs_str = "EPSG:4326"
        source_crs, _ = self.crs_service.parse_crs(source_crs_str)

        features: List[FeatureItem] = []
        projected_crs_used = source_crs_str

        # If no explicit Placemarks found, look for orphaned top-level geometry elements
        if not placemarks:
            candidate_geoms = (
                root.findall(".//{*}Polygon") +
                root.findall(".//{*}LineString") +
                root.findall(".//{*}Point") +
                root.findall(".//{*}MultiGeometry")
            )
            for idx, g_elem in enumerate(candidate_geoms, start=1):
                geom = self._parse_geometry_element(g_elem)
                if not geom or geom.is_empty:
                    continue

                meas_details, wgs84_geom, _, proj_epsg = self.measurement_service.compute_measurements(
                    geom, source_crs, fallback_source_crs_name=source_crs_str
                )
                projected_crs_used = proj_epsg

                centroid_coords = [round(wgs84_geom.centroid.x, 6), round(wgs84_geom.centroid.y, 6)]
                bbox_coords = [round(c, 6) for c in wgs84_geom.bounds]

                features.append(
                    FeatureItem(
                        feature_id=idx,
                        geometry_type=geom.geom_type,
                        geometry=mapping(wgs84_geom),
                        crs=source_crs_str,
                        properties={"name": f"Feature {idx}"},
                        measurements=meas_details,
                        centroid=centroid_coords,
                        bbox=bbox_coords,
                    )
                )
            return features, source_crs_str, projected_crs_used

        for idx, pm in enumerate(placemarks, start=1):
            properties = self._extract_placemark_properties(pm)
            pm_id = pm.attrib.get("id") or properties.get("name") or idx

            # Find geometry inside Placemark
            geom = None
            for g_tag in ("Polygon", "LineString", "Point", "MultiGeometry"):
                found_elem = pm.find(f".//{{*}}{g_tag}")
                if found_elem is not None:
                    geom = self._parse_geometry_element(found_elem)
                    if geom:
                        break

            if not geom or geom.is_empty:
                continue

            meas_details, wgs84_geom, _, proj_epsg = self.measurement_service.compute_measurements(
                geom, source_crs, fallback_source_crs_name=source_crs_str
            )
            projected_crs_used = proj_epsg

            centroid_coords = None
            bbox_coords = None
            if not wgs84_geom.is_empty:
                centroid = wgs84_geom.centroid
                centroid_coords = [round(centroid.x, 6), round(centroid.y, 6)]
                bbox_coords = [round(c, 6) for c in wgs84_geom.bounds]

            features.append(
                FeatureItem(
                    feature_id=pm_id,
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

    def parse_file(self, file_path: Path) -> Tuple[List[FeatureItem], str, str]:
        """Parses either .kml (plain XML) or .kmz (zip archive)."""
        suffix = file_path.suffix.lower()

        if suffix == ".kmz":
            # KMZ is a zip archive containing doc.kml
            with zipfile.ZipFile(file_path, "r") as zf:
                kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
                if not kml_names:
                    raise ValueError("KMZ archive does not contain any .kml document.")
                kml_bytes = zf.read(kml_names[0])
                kml_text = kml_bytes.decode("utf-8", errors="replace")
        else:
            kml_text = file_path.read_text(encoding="utf-8", errors="replace")

        return self.parse_kml_content(kml_text)


kml_parser = KMLParser()
