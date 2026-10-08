/**
 * GeoMeasure API - Frontend Client Controller
 * Clean, reactive JavaScript for geospatial visualization and measurement analytics.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Application State
  const state = {
    activeFileId: null,
    activeFileInfo: null,
    activeMeasurements: null,
    activeGeoJson: null,
    selectedFeatureId: null,
    areaUnit: "m2", // m2, km2, ha, ac
    lengthUnit: "m", // m, km, mi, ft
    filterType: "all",
    searchQuery: "",
    leafletLayers: {},
    currentGeoJsonLayer: null,
  };

  // DOM Elements
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const uploadProgress = document.getElementById("uploadProgress");
  const progressBar = document.getElementById("progressBar");
  const toast = document.getElementById("toast");
  const toastMessage = document.getElementById("toastMessage");

  // Metadata & KPI Elements
  const fileMetaCard = document.getElementById("fileMetaCard");
  const metaFileId = document.getElementById("metaFileId");
  const metaFilename = document.getElementById("metaFilename");
  const metaFeatureCount = document.getElementById("metaFeatureCount");
  const metaSourceCrs = document.getElementById("metaSourceCrs");
  const metaProjectedCrs = document.getElementById("metaProjectedCrs");
  const fileStatusBadge = document.getElementById("fileStatusBadge");

  const kpiCard = document.getElementById("kpiCard");
  const kpiAreaVal = document.getElementById("kpiAreaVal");
  const kpiLengthVal = document.getElementById("kpiLengthVal");

  // Inspector Elements
  const inspectorCard = document.getElementById("inspectorCard");
  const inspFeatureId = document.getElementById("inspFeatureId");
  const inspTypePill = document.getElementById("inspTypePill");
  const inspMeasurementRows = document.getElementById("inspMeasurementRows");
  const inspAttributes = document.getElementById("inspAttributes");

  // Table & Action Elements
  const tableSection = document.getElementById("tableSection");
  const featuresTableBody = document.getElementById("featuresTableBody");
  const tableSearchInput = document.getElementById("tableSearchInput");
  const btnFitBounds = document.getElementById("btnFitBounds");
  const btnExportGeoJSON = document.getElementById("btnExportGeoJSON");
  const btnExportCSV = document.getElementById("btnExportCSV");
  const btnRawApi = document.getElementById("btnRawApi");

  // Sample Loaders
  const loadSampleParcels = document.getElementById("loadSampleParcels");
  const loadSamplePipelines = document.getElementById("loadSamplePipelines");
  const loadSamplePoints = document.getElementById("loadSamplePoints");

  // Initialize Leaflet Map
  const map = L.map("map", {
    zoomControl: true,
    attributionControl: true,
  }).setView([20, 0], 2);

  // Basemap Tile Layers
  const darkBasemap = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
      subdomains: "abcd",
      maxZoom: 19,
    }
  );

  const satelliteBasemap = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      attribution: "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
      maxZoom: 19,
    }
  );

  const osmBasemap = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }
  );

  // Set default basemap
  darkBasemap.addTo(map);

  // Add basemap layer control
  L.control
    .layers(
      {
        "Dark Canvas (Recommended)": darkBasemap,
        "Satellite Imagery": satelliteBasemap,
        "OpenStreetMap Standard": osmBasemap,
      },
      null,
      { position: "topright" }
    )
    .addTo(map);

  // UI Toast Helper
  function showToast(message, type = "success") {
    toastMessage.textContent = message;
    toast.className = `toast show ${type}`;
    setTimeout(() => {
      toast.className = "toast";
    }, 4000);
  }

  // Progress Bar Helper
  function setProgress(percent) {
    if (percent === 0) {
      uploadProgress.style.display = "block";
      progressBar.style.width = "0%";
    } else if (percent >= 100) {
      progressBar.style.width = "100%";
      setTimeout(() => {
        uploadProgress.style.display = "none";
      }, 500);
    } else {
      uploadProgress.style.display = "block";
      progressBar.style.width = `${percent}%`;
    }
  }

  // Drag and Drop Handling
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("drag-active");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("drag-active");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  });

  dropzone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });

  // File Upload Handler
  async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append("file", file);

    setProgress(25);
    try {
      const response = await fetch("/api/files/", {
        method: "POST",
        body: formData,
      });

      setProgress(75);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      const fileInfo = await response.json();
      setProgress(100);
      showToast(`Processed '${fileInfo.filename}' (${fileInfo.feature_count} features)`);
      await loadFileData(fileInfo.id);
    } catch (err) {
      setProgress(100);
      showToast(err.message, "error");
    }
  }

  // Sample Loaders
  async function loadSample(sampleKey, label) {
    setProgress(30);
    try {
      const response = await fetch(`/api/files/load-sample/${sampleKey}`, {
        method: "POST",
      });
      setProgress(75);
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to load sample dataset");
      }
      const fileInfo = await response.json();
      setProgress(100);
      showToast(`Loaded ${label}`);
      await loadFileData(fileInfo.id);
    } catch (err) {
      setProgress(100);
      showToast(err.message, "error");
    }
  }

  loadSampleParcels.addEventListener("click", () => loadSample("parcels", "Land Parcels Shapefile"));
  loadSamplePipelines.addEventListener("click", () => loadSample("pipelines", "Utility Pipelines KML"));
  loadSamplePoints.addEventListener("click", () => loadSample("points", "Geodetic Benchmarks KML"));

  // Fetch Full File Data & Render
  async function loadFileData(fileId) {
    try {
      // Fetch Measurements and GeoJSON concurrently
      const [measRes, geoRes] = await Promise.all([
        fetch(`/api/files/${fileId}/measurements/`),
        fetch(`/api/files/${fileId}/geojson/`),
      ]);

      if (!measRes.ok || !geoRes.ok) {
        throw new Error("Failed to load processed file details.");
      }

      const measurementsData = await measRes.json();
      const geoJsonData = await geoRes.json();

      state.activeFileId = fileId;
      state.activeMeasurements = measurementsData;
      state.activeGeoJson = geoJsonData;

      // Update UI Panels
      renderFileMetadata(measurementsData);
      renderKPIs(measurementsData.summary);
      renderMapFeatures(geoJsonData);
      renderTableFeatures();

      // Show sections
      fileMetaCard.style.display = "block";
      kpiCard.style.display = "block";
      tableSection.style.display = "block";
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  // Render Metadata Card
  function renderFileMetadata(data) {
    metaFileId.textContent = data.file_id;
    metaFilename.textContent = data.filename;
    metaFeatureCount.textContent = data.feature_count;
    metaSourceCrs.textContent = data.crs;
    fileStatusBadge.textContent = "COMPLETED";

    const projCrs = data.projected_crs_used || "EPSG:3857";
    metaProjectedCrs.innerHTML = `
      Features converted to metric projected system: <strong>${projCrs}</strong>.<br>
      High-precision Euclidean planar calculations performed without angular degree distortion.
    `;
  }

  // Format Numbers
  function formatNum(val, decimals = 2) {
    if (val === null || val === undefined || isNaN(val)) return "-";
    return Number(val).toLocaleString("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  // Render Aggregate KPIs
  function renderKPIs(summary) {
    if (!summary) return;

    // Area KPI calculation
    let areaVal = 0;
    if (state.areaUnit === "m2") areaVal = summary.total_area_sq_m;
    else if (state.areaUnit === "km2") areaVal = summary.total_area_sq_km;
    else if (state.areaUnit === "ha") areaVal = summary.total_area_hectares;
    else if (state.areaUnit === "ac") areaVal = summary.total_area_acres;

    kpiAreaVal.textContent = formatNum(areaVal, state.areaUnit === "km2" ? 4 : 2);

    // Length KPI calculation
    let lenVal = 0;
    if (state.lengthUnit === "m") lenVal = summary.total_length_m;
    else if (state.lengthUnit === "km") lenVal = summary.total_length_km;
    else if (state.lengthUnit === "mi") lenVal = summary.total_length_miles;
    else if (state.lengthUnit === "ft") lenVal = summary.total_length_m * 3.28084;

    kpiLengthVal.textContent = formatNum(lenVal, state.lengthUnit === "km" || state.lengthUnit === "mi" ? 3 : 1);
  }

  // Unit Switcher Event Listeners
  document.querySelectorAll(".unit-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const unitType = btn.dataset.unitType;
      const unit = btn.dataset.unit;

      // Toggle active style within group
      const parent = btn.parentElement;
      parent.querySelectorAll(".unit-chip").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");

      if (unitType === "area") {
        state.areaUnit = unit;
      } else if (unitType === "length") {
        state.lengthUnit = unit;
      }

      if (state.activeMeasurements) {
        renderKPIs(state.activeMeasurements.summary);
        renderTableFeatures();
        if (state.selectedFeatureId !== null) {
          const selectedFeat = state.activeMeasurements.features.find(
            (f) => String(f.feature_id) === String(state.selectedFeatureId)
          );
          if (selectedFeat) renderInspector(selectedFeat);
        }
      }
    });
  });

  // Render Map Features with Leaflet
  function renderMapFeatures(geoJsonData) {
    // Remove previous layer
    if (state.currentGeoJsonLayer) {
      map.removeLayer(state.currentGeoJsonLayer);
    }
    state.leafletLayers = {};

    state.currentGeoJsonLayer = L.geoJSON(geoJsonData, {
      style: (feature) => {
        const geomType = feature.geometry.type;
        if (geomType.includes("Polygon")) {
          return {
            fillColor: "#10b981",
            weight: 2,
            opacity: 0.9,
            color: "#34d399",
            fillOpacity: 0.35,
          };
        } else if (geomType.includes("Line")) {
          return {
            color: "#6366f1",
            weight: 4,
            opacity: 0.85,
            lineJoin: "round",
          };
        }
        return {
          color: "#f59e0b",
          weight: 2,
        };
      },
      pointToLayer: (feature, latlng) => {
        return L.circleMarker(latlng, {
          radius: 7,
          fillColor: "#f59e0b",
          color: "#ffffff",
          weight: 2,
          opacity: 1,
          fillOpacity: 0.85,
        });
      },
      onEachFeature: (feature, layer) => {
        const featId = feature.id || feature.properties.__feature_id;
        state.leafletLayers[featId] = layer;

        const geomType = feature.geometry.type;
        const meas = feature.properties.__measurements || {};

        let tooltipHtml = `<strong>ID:</strong> ${featId} (${geomType})<br>`;
        if (meas.area) {
          tooltipHtml += `<strong>Area:</strong> ${formatNum(meas.area.sq_meters)} m²<br>`;
        }
        if (meas.length) {
          tooltipHtml += `<strong>Length:</strong> ${formatNum(meas.length.meters)} m<br>`;
        }

        layer.bindTooltip(tooltipHtml, { sticky: true, opacity: 0.9 });

        layer.on({
          mouseover: (e) => {
            const target = e.target;
            if (geomType.includes("Polygon")) {
              target.setStyle({ fillOpacity: 0.65, weight: 3 });
            } else if (geomType.includes("Line")) {
              target.setStyle({ weight: 6, opacity: 1 });
            }
          },
          mouseout: (e) => {
            if (String(state.selectedFeatureId) !== String(featId)) {
              state.currentGeoJsonLayer.resetStyle(e.target);
            }
          },
          click: (e) => {
            L.DomEvent.stopPropagation(e);
            selectFeature(featId);
          },
        });
      },
    }).addTo(map);

    // Zoom and pan to fit bounds
    try {
      const bounds = state.currentGeoJsonLayer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
      }
    } catch (e) {}
  }

  // Select Feature
  function selectFeature(featId) {
    state.selectedFeatureId = featId;

    if (!state.activeMeasurements) return;
    const feat = state.activeMeasurements.features.find(
      (f) => String(f.feature_id) === String(featId)
    );
    if (!feat) return;

    renderInspector(feat);

    // Highlight map layer
    const layer = state.leafletLayers[featId];
    if (layer) {
      if (layer.getBounds) {
        map.panTo(layer.getBounds().getCenter());
      } else if (layer.getLatLng) {
        map.panTo(layer.getLatLng());
      }

      if (layer.setStyle) {
        layer.setStyle({
          color: "#38bdf8",
          weight: 4,
          fillColor: "#38bdf8",
          fillOpacity: 0.5,
        });
      }
    }

    // Highlight table row
    document.querySelectorAll("#featuresTableBody tr").forEach((tr) => {
      if (tr.dataset.featureId === String(featId)) {
        tr.classList.add("selected");
        tr.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } else {
        tr.classList.remove("selected");
      }
    });
  }

  // Render Feature Inspector Drawer
  function renderInspector(feat) {
    inspectorCard.style.display = "block";
    inspFeatureId.textContent = feat.feature_id;
    inspTypePill.textContent = feat.geometry_type;
    inspTypePill.className = `feature-pill ${feat.geometry_type.toLowerCase().includes("polygon") ? "polygon" : feat.geometry_type.toLowerCase().includes("line") ? "linestring" : "point"}`;

    const m = feat.measurements;
    let rowsHtml = "";

    // Area measurements
    if (m.area) {
      let areaFormatted = "";
      if (state.areaUnit === "m2") areaFormatted = `${formatNum(m.area.sq_meters)} m²`;
      else if (state.areaUnit === "km2") areaFormatted = `${formatNum(m.area.sq_kilometers, 4)} km²`;
      else if (state.areaUnit === "ha") areaFormatted = `${formatNum(m.area.hectares, 3)} ha`;
      else if (state.areaUnit === "ac") areaFormatted = `${formatNum(m.area.acres, 3)} acres`;

      rowsHtml += `
        <div class="file-meta-row">
          <span class="file-meta-label">Calculated Area</span>
          <span class="file-meta-value" style="color: var(--accent-emerald);">${areaFormatted}</span>
        </div>
      `;
    }

    // Perimeter measurements
    if (m.perimeter) {
      rowsHtml += `
        <div class="file-meta-row">
          <span class="file-meta-label">Perimeter</span>
          <span class="file-meta-value">${formatNum(m.perimeter.meters)} m (${formatNum(m.perimeter.feet)} ft)</span>
        </div>
      `;
    }

    // Length measurements
    if (m.length) {
      let lenFormatted = "";
      if (state.lengthUnit === "m") lenFormatted = `${formatNum(m.length.meters)} m`;
      else if (state.lengthUnit === "km") lenFormatted = `${formatNum(m.length.kilometers, 3)} km`;
      else if (state.lengthUnit === "mi") lenFormatted = `${formatNum(m.length.miles, 3)} miles`;
      else if (state.lengthUnit === "ft") lenFormatted = `${formatNum(m.length.feet)} ft`;

      rowsHtml += `
        <div class="file-meta-row">
          <span class="file-meta-label">Path Length</span>
          <span class="file-meta-value" style="color: var(--accent-indigo);">${lenFormatted}</span>
        </div>
      `;
    }

    // Geodesic Ellipsoidal Reference Metrics
    if (m.geodesic_area_sq_m) {
      rowsHtml += `
        <div class="file-meta-row">
          <span class="file-meta-label">Geodesic Area (WGS84)</span>
          <span class="file-meta-value">${formatNum(m.geodesic_area_sq_m)} m²</span>
        </div>
      `;
    }
    if (m.geodesic_length_m) {
      rowsHtml += `
        <div class="file-meta-row">
          <span class="file-meta-label">Geodesic Length (WGS84)</span>
          <span class="file-meta-value">${formatNum(m.geodesic_length_m)} m</span>
        </div>
      `;
    }

    // Graceful handling note for Point
    if (!m.supported && m.notes) {
      rowsHtml += `
        <div class="file-meta-row">
          <span class="file-meta-label">Measurement Status</span>
          <span class="file-meta-value" style="color: var(--accent-amber); font-size: 0.75rem;">${m.notes}</span>
        </div>
      `;
    }

    // Projected CRS used
    rowsHtml += `
      <div class="file-meta-row">
        <span class="file-meta-label">Target Projected CRS</span>
        <span class="file-meta-value">${m.projected_crs}</span>
      </div>
    `;

    inspMeasurementRows.innerHTML = rowsHtml;

    // Attributes list
    const props = feat.properties || {};
    const propKeys = Object.keys(props).filter((k) => !k.startsWith("__"));
    if (propKeys.length === 0) {
      inspAttributes.innerHTML = `<span style="color: var(--text-faint);">No attribute properties present.</span>`;
    } else {
      let attrTableHtml = `<table style="width: 100%; border-collapse: collapse;">`;
      propKeys.forEach((key) => {
        attrTableHtml += `
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
            <td style="color: var(--text-faint); padding: 3px 0; width: 40%;">${key}:</td>
            <td style="color: var(--text-main); font-weight: 500; padding: 3px 0;">${props[key]}</td>
          </tr>
        `;
      });
      attrTableHtml += `</table>`;
      inspAttributes.innerHTML = attrTableHtml;
    }
  }

  // Render Features Data Table
  function renderTableFeatures() {
    if (!state.activeMeasurements) return;

    let features = state.activeMeasurements.features;

    // Filter by type
    if (state.filterType !== "all") {
      features = features.filter((f) =>
        f.geometry_type.toLowerCase().includes(state.filterType.toLowerCase())
      );
    }

    // Filter by search query
    if (state.searchQuery.trim()) {
      const q = state.searchQuery.toLowerCase();
      features = features.filter((f) => {
        const idMatch = String(f.feature_id).toLowerCase().includes(q);
        const propsMatch = JSON.stringify(f.properties).toLowerCase().includes(q);
        return idMatch || propsMatch;
      });
    }

    featuresTableBody.innerHTML = "";

    if (features.length === 0) {
      featuresTableBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
            No features match the selected filter criteria.
          </td>
        </tr>
      `;
      return;
    }

    features.forEach((feat) => {
      const tr = document.createElement("tr");
      tr.dataset.featureId = String(feat.feature_id);
      if (String(state.selectedFeatureId) === String(feat.feature_id)) {
        tr.classList.add("selected");
      }

      // Format Area
      let areaStr = "-";
      if (feat.measurements.area) {
        if (state.areaUnit === "m2") areaStr = `${formatNum(feat.measurements.area.sq_meters)} m²`;
        else if (state.areaUnit === "km2") areaStr = `${formatNum(feat.measurements.area.sq_kilometers, 4)} km²`;
        else if (state.areaUnit === "ha") areaStr = `${formatNum(feat.measurements.area.hectares, 3)} ha`;
        else if (state.areaUnit === "ac") areaStr = `${formatNum(feat.measurements.area.acres, 3)} ac`;
      }

      // Format Length / Perimeter
      let lenStr = "-";
      if (feat.measurements.length) {
        if (state.lengthUnit === "m") lenStr = `${formatNum(feat.measurements.length.meters)} m`;
        else if (state.lengthUnit === "km") lenStr = `${formatNum(feat.measurements.length.kilometers, 3)} km`;
        else if (state.lengthUnit === "mi") lenStr = `${formatNum(feat.measurements.length.miles, 3)} mi`;
        else if (state.lengthUnit === "ft") lenStr = `${formatNum(feat.measurements.length.feet)} ft`;
      } else if (feat.measurements.perimeter) {
        lenStr = `${formatNum(feat.measurements.perimeter.meters)} m (perim)`;
      }

      // Attribute preview snippet
      const props = feat.properties || {};
      const previewKeys = Object.keys(props).filter((k) => !k.startsWith("__")).slice(0, 2);
      const previewStr = previewKeys.map((k) => `${k}: ${props[k]}`).join(", ") || "None";

      tr.innerHTML = `
        <td style="font-weight: 600; font-family: var(--font-mono);">${feat.feature_id}</td>
        <td>
          <span class="feature-pill ${feat.geometry_type.toLowerCase().includes("polygon") ? "polygon" : feat.geometry_type.toLowerCase().includes("line") ? "linestring" : "point"}">
            ${feat.geometry_type}
          </span>
        </td>
        <td style="font-family: var(--font-mono); color: var(--accent-emerald);">${areaStr}</td>
        <td style="font-family: var(--font-mono); color: var(--accent-indigo);">${lenStr}</td>
        <td style="font-size: 0.75rem; color: var(--text-muted);">${feat.measurements.projected_crs}</td>
        <td style="font-size: 0.75rem; color: var(--text-muted); max-width: 220px; overflow: hidden; text-overflow: ellipsis;">${previewStr}</td>
      `;

      tr.addEventListener("click", () => selectFeature(feat.feature_id));
      featuresTableBody.appendChild(tr);
    });
  }

  // Table Filter Buttons
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.filterType = btn.dataset.filter;
      renderTableFeatures();
    });
  });

  // Table Search Input
  tableSearchInput.addEventListener("input", (e) => {
    state.searchQuery = e.target.value;
    renderTableFeatures();
  });

  // Fit Bounds Button
  btnFitBounds.addEventListener("click", () => {
    if (state.currentGeoJsonLayer) {
      try {
        const bounds = state.currentGeoJsonLayer.getBounds();
        if (bounds.isValid()) {
          map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
        }
      } catch (e) {}
    }
  });

  // Export GeoJSON
  btnExportGeoJSON.addEventListener("click", () => {
    if (!state.activeFileId) return;
    window.open(`/api/files/${state.activeFileId}/geojson/`, "_blank");
  });

  // Export CSV
  btnExportCSV.addEventListener("click", () => {
    if (!state.activeFileId) return;
    window.location.href = `/api/files/${state.activeFileId}/export/csv`;
  });

  // Open Raw API
  btnRawApi.addEventListener("click", () => {
    if (!state.activeFileId) return;
    window.open(`/api/files/${state.activeFileId}/measurements/`, "_blank");
  });

  // Check initial API health on page load
  fetch("/api/health")
    .then((r) => r.json())
    .then((data) => {
      const badge = document.getElementById("systemStatusBadge");
      badge.innerHTML = `<span class="pulse-dot"></span> API ${data.status.toUpperCase()}`;
    })
    .catch(() => {
      const badge = document.getElementById("systemStatusBadge");
      badge.className = "badge-status";
      badge.style.color = "var(--accent-rose)";
      badge.innerHTML = `Offline`;
    });
});
