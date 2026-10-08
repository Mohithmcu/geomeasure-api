"""Script to generate realistic test geospatial datasets (Shapefiles and KML)."""

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
import shapefile

SAMPLES_DIR = Path(__file__).parent / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

WGS84_PRJ = (
    'GEOGCS["GCS_WGS_1984",'
    'DATUM["D_WGS_1984",'
    'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]]'
)


def create_parcels_shapefile():
    """Generates sample_land_parcels.zip containing realistic agricultural land parcels."""
    temp_dir = tempfile.mkdtemp(prefix="sample_shp_")
    try:
        shp_stem = "land_parcels"
        shp_path = os.path.join(temp_dir, shp_stem)

        # Initialize Shapefile writer for Polygons
        w = shapefile.Writer(shp_path, shapeType=shapefile.POLYGON)
        w.field("PARCEL_ID", "C", size=20)
        w.field("LAND_USE", "C", size=30)
        w.field("FARMER", "C", size=40)
        w.field("IRRIGATED", "C", size=5)

        # Region around Fresno, Central Valley California (approx 36.74° N, -119.78° W)
        # Parcel 1: Vineyard (Clockwise order for Shapefile exterior ring)
        w.poly([[
            [-119.780, 36.740],
            [-119.780, 36.748],
            [-119.770, 36.748],
            [-119.770, 36.740],
            [-119.780, 36.740]
        ]])
        w.record("P-101", "Vineyard", "Valley Vista Estates", "YES")

        # Parcel 2: Almond Orchard (Clockwise)
        w.poly([[
            [-119.770, 36.740],
            [-119.770, 36.752],
            [-119.758, 36.752],
            [-119.758, 36.740],
            [-119.770, 36.740]
        ]])
        w.record("P-102", "Almond Orchard", "Sunstone Agri Group", "YES")

        # Parcel 3: Solar Array Farm (Clockwise)
        w.poly([[
            [-119.782, 36.750],
            [-119.784, 36.762],
            [-119.774, 36.762],
            [-119.772, 36.750],
            [-119.782, 36.750]
        ]])
        w.record("P-103", "Solar Power Station", "Pacific Clean Energy", "NO")

        # Parcel 4: Organic Wheat Field (Clockwise)
        w.poly([[
            [-119.756, 36.742],
            [-119.758, 36.755],
            [-119.744, 36.755],
            [-119.742, 36.742],
            [-119.756, 36.742]
        ]])
        w.record("P-104", "Organic Wheat Field", "Highland Grain LLC", "NO")

        w.close()

        # Write .prj file
        with open(f"{shp_path}.prj", "w", encoding="utf-8") as f:
            f.write(WGS84_PRJ)

        # Zip shapefile components
        zip_target = SAMPLES_DIR / "sample_land_parcels.zip"
        with zipfile.ZipFile(zip_target, "w", zipfile.ZIP_DEFLATED) as zf:
            for ext in (".shp", ".shx", ".dbf", ".prj"):
                fpath = f"{shp_path}{ext}"
                if os.path.exists(fpath):
                    zf.write(fpath, arcname=f"{shp_stem}{ext}")

        print(f"Created: {zip_target}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def create_pipeline_kml():
    """Generates sample_utility_network.kml containing pipelines and facilities."""
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Regional Energy &amp; Water Network</name>
    <description>Infrastructure pipelines, service easements, and pumping stations</description>

    <!-- LineString 1: Main High-Pressure Gas Line -->
    <Placemark id="PIPE-NORTH-01">
      <name>North Gas Transmission Main</name>
      <description>Steel 24-inch natural gas transmission backbone</description>
      <ExtendedData>
        <Data name="Material"><value>API 5L X65 Steel</value></Data>
        <Data name="Diameter_mm"><value>600</value></Data>
        <Data name="Operating_Pressure_Bar"><value>68.5</value></Data>
        <Data name="Installation_Year"><value>2021</value></Data>
      </ExtendedData>
      <LineString>
        <extrude>1</extrude>
        <tessellate>1</tessellate>
        <coordinates>
          -0.142,51.501,0
          -0.128,51.508,0
          -0.115,51.516,0
          -0.098,51.524,0
          -0.082,51.535,0
        </coordinates>
      </LineString>
    </Placemark>

    <!-- LineString 2: Regional Aqueduct Trunk -->
    <Placemark id="PIPE-AQUEDUCT-02">
      <name>East Thames Potable Water Trunk</name>
      <description>Prestressed concrete water aqueduct connecting reservoirs</description>
      <ExtendedData>
        <Data name="Material"><value>Ductile Iron</value></Data>
        <Data name="Diameter_mm"><value>900</value></Data>
        <Data name="Flow_Rate_m3_h"><value>4500</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>
          -0.082,51.535,0
          -0.065,51.542,0
          -0.048,51.551,0
          -0.032,51.562,0
        </coordinates>
      </LineString>
    </Placemark>

    <!-- Polygon: Terminal Compressor Station Easement -->
    <Placemark id="FAC-PUMP-01">
      <name>St. Jude Gas Compressor Facility</name>
      <description>Fenced perimeter and safety buffer zone</description>
      <ExtendedData>
        <Data name="Zone"><value>Industrial Heavy</value></Data>
        <Data name="Security_Level"><value>Class 4</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -0.146,51.498,0
              -0.138,51.498,0
              -0.138,51.503,0
              -0.146,51.503,0
              -0.146,51.498,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- Point: Supervisory SCADA Monitoring Station -->
    <Placemark id="SCADA-MON-09">
      <name>Pressure Monitoring Station Beta</name>
      <description>Automated telemetry telemetry beacon</description>
      <ExtendedData>
        <Data name="Telemetry"><value>Satellite / 4G Fallback</value></Data>
        <Data name="Battery_Health"><value>100%</value></Data>
      </ExtendedData>
      <Point>
        <coordinates>-0.115,51.516,25</coordinates>
      </Point>
    </Placemark>

  </Document>
</kml>
"""
    target = SAMPLES_DIR / "sample_utility_network.kml"
    target.write_text(kml_content, encoding="utf-8")
    print(f"Created: {target}")


def create_points_kml():
    """Generates sample_points_of_interest.kml to test graceful handling of Points."""
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Geodetic Survey Control Benchmarks</name>
    <Placemark id="BM-001">
      <name>Triangulation Pillar Alpha</name>
      <description>High precision geodetic GPS benchmark</description>
      <Point>
        <coordinates>77.5946,12.9716,920</coordinates>
      </Point>
    </Placemark>
    <Placemark id="BM-002">
      <name>Triangulation Pillar Bravo</name>
      <description>Seismic accelerometer station</description>
      <Point>
        <coordinates>77.6102,12.9854,915</coordinates>
      </Point>
    </Placemark>
    <Placemark id="BM-003">
      <name>Weather Radar Tower</name>
      <description>Doppler weather radar beacon</description>
      <Point>
        <coordinates>77.5812,12.9601,945</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>
"""
    target = SAMPLES_DIR / "sample_points_of_interest.kml"
    target.write_text(kml_content, encoding="utf-8")
    print(f"Created: {target}")


if __name__ == "__main__":
    create_parcels_shapefile()
    create_pipeline_kml()
    create_points_kml()
    print("All sample datasets successfully generated.")
