const levelValue = document.getElementById("level-value");
const levelCaption = document.getElementById("level-caption");
const gallonsRemaining = document.getElementById("gallons-remaining");
const tankFillFront = document.getElementById("tank-fill-front");
const tankFillBack = document.getElementById("tank-fill-back");
const statsLabel = document.getElementById("stats-label");
const readingCount = document.getElementById("reading-count");
const avgLevel = document.getElementById("avg-level");
const levelRange = document.getElementById("level-range");
const avgConfidence = document.getElementById("avg-confidence");
const latestImage = document.getElementById("latest-image");
const latestMeta = document.getElementById("latest-meta");
const chart = document.getElementById("history-chart");
const readingsBody = document.getElementById("readings-body");
const tableCaption = document.getElementById("table-caption");
const pagination = document.getElementById("pagination");
const collectNowButton = document.getElementById("collect-now");
const refreshBtn = document.getElementById("refresh-btn");
const flushHistoryButton = document.getElementById("flush-history");
const bottomActions = document.getElementById("bottom-actions");
const actionStatus = document.getElementById("action-status");
const rangeSelector = document.getElementById("range-selector");

const chartModal = document.getElementById("chart-modal");
const chartModalClose = document.getElementById("chart-modal-close");
const chartModalSvg = document.getElementById("chart-modal-svg");

const readingModal = document.getElementById("reading-modal");
const modalClose = document.getElementById("modal-close");
const modalCropImage = document.getElementById("modal-crop-image");
const modalDebugImage = document.getElementById("modal-debug-image");
const modalMeta = document.getElementById("modal-meta");
const modalActions = document.getElementById("modal-actions");
const modalDelete = document.getElementById("modal-delete");

let flushEnabled = false;
let activeReadingId = null;
let currentRange = "1m";
let currentPage = 0;
let allReadings = [];
const PAGE_SIZE = 12;

const RANGES = {
  "24h": { hours: 24, label: "Last 24 Hours" },
  "7d": { hours: 168, label: "Last 7 Days" },
  "1m": { hours: 730, label: "Last Month" },
  "6m": { hours: 4380, label: "Last 6 Months" },
  "all": { hours: null, label: "All Time" },
};

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

const shortDateFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
});

const shortTimeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "numeric",
  minute: "2-digit",
});

function formatPercent(value) {
  return value == null ? "--" : `${value.toFixed(1)}%`;
}

function formatConfidence(value) {
  return value == null ? "--" : `${Math.round(value * 100)}%`;
}

function formatGallons(value) {
  return value == null ? "--" : `${Math.round(value).toLocaleString()} gal`;
}

function sinceParam(range) {
  const info = RANGES[range];
  if (!info || !info.hours) return "";
  const since = new Date(Date.now() - info.hours * 3600000).toISOString();
  return `&since=${encodeURIComponent(since)}`;
}

function isMobile() {
  return window.innerWidth <= 640;
}

function setTankLevel(percent) {
  const pct = Math.max(0, Math.min(100, percent ?? 0)) / 100;

  const frontH = pct * 230;
  const frontY = 280 - frontH;
  tankFillFront.setAttribute("y", String(frontY));
  tankFillFront.setAttribute("height", String(frontH));
  tankFillFront.setAttribute("fill", "url(#water-gradient-front)");

  const backH = pct * 230;
  const backY = 260 - backH;
  tankFillBack.setAttribute("y", String(backY));
  tankFillBack.setAttribute("height", String(backH));
  tankFillBack.setAttribute("fill", "url(#water-gradient-back)");
}

function setCurrentLevel(latest) {
  if (!latest) {
    levelValue.textContent = "--";
    levelCaption.textContent = "No reading yet";
    gallonsRemaining.textContent = "-- gallons remaining";
    setTankLevel(0);
    latestImage.removeAttribute("src");
    latestMeta.textContent = "Waiting for a reading";
    return;
  }

  levelValue.textContent = formatPercent(latest.percent_full);
  levelCaption.textContent = `${latest.marker_found ? "Marker found" : "Marker missing"} \u2022 ${dateFormatter.format(new Date(latest.captured_at))}`;
  gallonsRemaining.textContent = `${formatGallons(latest.gallons_remaining)} remaining`;
  setTankLevel(latest.percent_full);

  if (latest.debug_image_url || latest.crop_image_url) {
    latestImage.src = latest.debug_image_url || latest.crop_image_url;
    latestMeta.textContent = `Confidence ${formatConfidence(latest.confidence)} \u2022 Y ${latest.marker_center_y == null ? "--" : latest.marker_center_y.toFixed(1)}`;
  } else {
    latestImage.removeAttribute("src");
    latestMeta.textContent = "No crop image available";
  }
}

function computeSummary(readings) {
  const valid = readings.filter((r) => r.percent_full != null);
  if (!valid.length) {
    return {
      reading_count: readings.length,
      avg_percent_full: null,
      min_percent_full: null,
      max_percent_full: null,
      avg_confidence: null,
    };
  }
  const levels = valid.map((r) => r.percent_full);
  const confs = valid.map((r) => r.confidence);
  return {
    reading_count: readings.length,
    avg_percent_full: levels.reduce((a, b) => a + b, 0) / levels.length,
    min_percent_full: Math.min(...levels),
    max_percent_full: Math.max(...levels),
    avg_confidence: confs.reduce((a, b) => a + b, 0) / confs.length,
  };
}

function setSummary(summary) {
  statsLabel.textContent = RANGES[currentRange].label;
  readingCount.textContent = String(summary.reading_count ?? 0);
  avgLevel.textContent = formatPercent(summary.avg_percent_full);
  if (summary.min_percent_full == null || summary.max_percent_full == null) {
    levelRange.textContent = "--";
  } else {
    levelRange.textContent = `${summary.min_percent_full.toFixed(1)}% \u2013 ${summary.max_percent_full.toFixed(1)}%`;
  }
  avgConfidence.textContent = formatConfidence(summary.avg_confidence);
}

function formatAxisDate(date, range) {
  if (range === "24h") return shortTimeFormatter.format(date);
  return shortDateFormatter.format(date);
}

function buildChart(svgEl, readings, options = {}) {
  svgEl.innerHTML = "";

  const svgW = options.width || 900;
  const svgH = options.height || 340;
  const clickable = options.clickable !== false;
  svgEl.setAttribute("viewBox", `0 0 ${svgW} ${svgH}`);

  const points = readings
    .filter((reading) => reading.percent_full != null)
    .reverse();

  if (points.length < 2) {
    const message = document.createElementNS("http://www.w3.org/2000/svg", "text");
    message.setAttribute("x", String(svgW / 2));
    message.setAttribute("y", String(svgH / 2));
    message.setAttribute("text-anchor", "middle");
    message.setAttribute("fill", "#5d6c63");
    message.setAttribute("font-size", "14");
    message.setAttribute("font-family", "Avenir Next, Segoe UI, sans-serif");
    message.textContent = "Not enough readings yet";
    svgEl.appendChild(message);
    return;
  }

  const padLeft = 52;
  const padRight = 20;
  const padTop = 24;
  const padBottom = 44;
  const usableW = svgW - padLeft - padRight;
  const usableH = svgH - padTop - padBottom;

  const levels = points.map((r) => r.percent_full);
  const dataMin = Math.min(...levels);
  const dataMax = Math.max(...levels);
  const dataSpan = dataMax - dataMin;
  const yPad = Math.max(dataSpan * 0.2, 2);
  const yMin = Math.max(0, Math.floor((dataMin - yPad) / 5) * 5);
  const yMax = Math.min(100, Math.ceil((dataMax + yPad) / 5) * 5);
  const yRange = yMax - yMin || 10;

  let yStep;
  if (yRange <= 10) yStep = 2;
  else if (yRange <= 25) yStep = 5;
  else if (yRange <= 60) yStep = 10;
  else yStep = 25;

  for (let pct = yMin; pct <= yMax; pct += yStep) {
    const y = padTop + usableH - ((pct - yMin) / yRange) * usableH;

    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", String(padLeft));
    line.setAttribute("x2", String(svgW - padRight));
    line.setAttribute("y1", String(y));
    line.setAttribute("y2", String(y));
    line.setAttribute("stroke", "rgba(33, 48, 39, 0.10)");
    svgEl.appendChild(line);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(padLeft - 8));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("class", "chart-axis-label");
    label.textContent = `${pct}%`;
    svgEl.appendChild(label);
  }

  const coords = points.map((reading, index) => {
    const x = padLeft + (usableW / (points.length - 1)) * index;
    const y = padTop + usableH - ((reading.percent_full - yMin) / yRange) * usableH;
    return { x, y, reading };
  });

  const tickCount = Math.min(6, points.length);
  for (let i = 0; i < tickCount; i++) {
    const idx = Math.round((i / (tickCount - 1)) * (points.length - 1));
    const { x, reading } = coords[idx];
    const date = new Date(reading.captured_at);

    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(x));
    label.setAttribute("y", String(svgH - 8));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "chart-axis-label");
    label.textContent = formatAxisDate(date, currentRange);
    svgEl.appendChild(label);

    const tick = document.createElementNS("http://www.w3.org/2000/svg", "line");
    tick.setAttribute("x1", String(x));
    tick.setAttribute("x2", String(x));
    tick.setAttribute("y1", String(padTop + usableH));
    tick.setAttribute("y2", String(padTop + usableH + 6));
    tick.setAttribute("stroke", "rgba(33, 48, 39, 0.2)");
    svgEl.appendChild(tick);
  }

  const pathD = coords
    .map(({ x, y }, i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", pathD);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "#c2185b");
  path.setAttribute("stroke-width", "3");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  svgEl.appendChild(path);

  const maxDots = 60;
  let dotIndices;
  if (coords.length <= maxDots) {
    dotIndices = coords.map((_, i) => i);
  } else {
    dotIndices = [];
    for (let i = 0; i < maxDots; i++) {
      dotIndices.push(Math.round((i / (maxDots - 1)) * (coords.length - 1)));
    }
  }

  for (const idx of dotIndices) {
    const { x, y, reading } = coords[idx];

    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    dot.setAttribute("cx", String(x));
    dot.setAttribute("cy", String(y));
    dot.setAttribute("r", coords.length > 30 ? "3.5" : "5");
    dot.setAttribute("fill", "#f48fb1");
    dot.setAttribute("stroke", "#880e4f");
    dot.setAttribute("stroke-width", coords.length > 30 ? "1.5" : "2");
    dot.setAttribute("class", "chart-dot");
    if (clickable) {
      dot.style.cursor = "pointer";
      dot.addEventListener("click", (e) => {
        e.stopPropagation();
        openReadingModal(reading);
      });
    }
    svgEl.appendChild(dot);

    if (coords.length <= 24) {
      const lbl = document.createElementNS("http://www.w3.org/2000/svg", "text");
      lbl.setAttribute("x", String(x));
      lbl.setAttribute("y", String(y - 10));
      lbl.setAttribute("text-anchor", "middle");
      lbl.setAttribute("class", "chart-tooltip");
      lbl.textContent = `${reading.percent_full.toFixed(0)}%`;
      svgEl.appendChild(lbl);
    }
  }
}

function renderChart(readings) {
  buildChart(chart, readings);
}

function renderTable(readings) {
  readingsBody.innerHTML = "";

  if (!readings.length) {
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="6" class="empty">No readings yet</td>';
    readingsBody.appendChild(row);
    tableCaption.textContent = "Newest first";
    pagination.innerHTML = "";
    return;
  }

  const totalPages = Math.ceil(readings.length / PAGE_SIZE);
  if (currentPage >= totalPages) currentPage = totalPages - 1;
  const start = currentPage * PAGE_SIZE;
  const pageItems = readings.slice(start, start + PAGE_SIZE);

  tableCaption.textContent = `${readings.length} readings \u2022 Page ${currentPage + 1} of ${totalPages}`;

  for (const reading of pageItems) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${dateFormatter.format(new Date(reading.captured_at))}</td>
      <td>${formatPercent(reading.percent_full)}</td>
      <td>${formatGallons(reading.gallons_remaining)}</td>
      <td>${reading.marker_center_y == null ? "--" : reading.marker_center_y.toFixed(1)}</td>
      <td>${formatConfidence(reading.confidence)}</td>
      <td>${reading.source_kind}</td>
    `;
    row.addEventListener("click", () => openReadingModal(reading));
    readingsBody.appendChild(row);
  }

  renderPagination(totalPages);
}

function renderPagination(totalPages) {
  pagination.innerHTML = "";
  if (totalPages <= 1) return;

  const prevBtn = document.createElement("button");
  prevBtn.className = "page-btn";
  prevBtn.textContent = "\u2039 Prev";
  prevBtn.disabled = currentPage === 0;
  prevBtn.addEventListener("click", () => { currentPage--; renderTable(allReadings); });
  pagination.appendChild(prevBtn);

  const maxVisible = 5;
  let startPage = Math.max(0, currentPage - Math.floor(maxVisible / 2));
  let endPage = Math.min(totalPages, startPage + maxVisible);
  if (endPage - startPage < maxVisible) startPage = Math.max(0, endPage - maxVisible);

  for (let i = startPage; i < endPage; i++) {
    const btn = document.createElement("button");
    btn.className = `page-btn${i === currentPage ? " active" : ""}`;
    btn.textContent = String(i + 1);
    btn.addEventListener("click", () => { currentPage = i; renderTable(allReadings); });
    pagination.appendChild(btn);
  }

  const nextBtn = document.createElement("button");
  nextBtn.className = "page-btn";
  nextBtn.textContent = "Next \u203a";
  nextBtn.disabled = currentPage >= totalPages - 1;
  nextBtn.addEventListener("click", () => { currentPage++; renderTable(allReadings); });
  pagination.appendChild(nextBtn);
}

function openReadingModal(reading) {
  activeReadingId = reading.id;

  if (reading.crop_image_url) {
    modalCropImage.src = reading.crop_image_url;
    modalCropImage.parentElement.hidden = false;
  } else {
    modalCropImage.removeAttribute("src");
    modalCropImage.parentElement.hidden = true;
  }

  if (reading.debug_image_url) {
    modalDebugImage.src = reading.debug_image_url;
    modalDebugImage.parentElement.hidden = false;
  } else {
    modalDebugImage.removeAttribute("src");
    modalDebugImage.parentElement.hidden = true;
  }

  modalMeta.innerHTML = `
    <div><dt>Captured</dt><dd>${dateFormatter.format(new Date(reading.captured_at))}</dd></div>
    <div><dt>Level</dt><dd>${formatPercent(reading.percent_full)}</dd></div>
    <div><dt>Gallons</dt><dd>${formatGallons(reading.gallons_remaining)}</dd></div>
    <div><dt>Confidence</dt><dd>${formatConfidence(reading.confidence)}</dd></div>
    <div><dt>Marker Y</dt><dd>${reading.marker_center_y == null ? "--" : reading.marker_center_y.toFixed(1)}</dd></div>
    <div><dt>Source</dt><dd>${reading.source_kind}</dd></div>
  `;

  modalActions.hidden = !flushEnabled;
  readingModal.hidden = false;
}

function closeReadingModal() {
  readingModal.hidden = true;
  activeReadingId = null;
}

modalClose.addEventListener("click", closeReadingModal);

readingModal.addEventListener("click", (e) => {
  if (e.target === readingModal) closeReadingModal();
});

modalDelete.addEventListener("click", async () => {
  const password = window.prompt("Enter the flush password to delete this reading.");
  if (!password) return;

  const confirmed = window.confirm("Delete this reading and its images? This cannot be undone.");
  if (!confirmed) return;

  modalDelete.disabled = true;

  try {
    const response = await fetch(`/api/readings/${activeReadingId}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || "Delete failed");
    }

    closeReadingModal();
    await loadDashboard();
  } catch (error) {
    window.alert(error?.message || "Delete failed");
  } finally {
    modalDelete.disabled = false;
  }
});

// Chart modal for mobile
chart.addEventListener("click", () => {
  if (!isMobile()) return;
  buildChart(chartModalSvg, allReadings, { width: 900, height: 500, clickable: false });
  chartModal.hidden = false;
});

chartModalClose.addEventListener("click", () => { chartModal.hidden = true; });
chartModal.addEventListener("click", (e) => {
  if (e.target === chartModal) chartModal.hidden = true;
});

// Range selector
rangeSelector.addEventListener("click", (e) => {
  const btn = e.target.closest(".range-btn");
  if (!btn) return;
  const range = btn.dataset.range;
  if (range === currentRange) return;

  currentRange = range;
  currentPage = 0;
  rangeSelector.querySelectorAll(".range-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  loadDashboard();
});

// Refresh button
refreshBtn.addEventListener("click", () => {
  refreshBtn.disabled = true;
  loadDashboard()
    .catch(() => {})
    .finally(() => { refreshBtn.disabled = false; });
});

async function loadDashboard() {
  const [statusResponse, readingsResponse] = await Promise.all([
    fetch("/api/status"),
    fetch(`/api/readings?limit=10000${sinceParam(currentRange)}`),
  ]);

  if (!statusResponse.ok || !readingsResponse.ok) {
    throw new Error("Unable to load dashboard data");
  }

  const status = await statusResponse.json();
  const readings = await readingsResponse.json();

  flushEnabled = !!status.admin?.flush_enabled;
  bottomActions.hidden = !flushEnabled;

  const collectRemaining = status.collect_remaining ?? 5;
  collectNowButton.disabled = collectRemaining <= 0;
  collectNowButton.textContent = collectRemaining <= 0
    ? "Rate Limited"
    : collectRemaining < 5
      ? `New Reading (${collectRemaining} left)`
      : "New Reading";

  allReadings = readings.items;
  setCurrentLevel(status.latest);
  setSummary(computeSummary(allReadings));
  renderChart(allReadings);
  renderTable(allReadings);
}

collectNowButton.addEventListener("click", async () => {
  collectNowButton.disabled = true;
  actionStatus.textContent = "Collecting a fresh snapshot...";

  try {
    const response = await fetch("/api/collect", { method: "POST" });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || "Collect failed");
    }

    actionStatus.textContent = "Snapshot collected";
    await loadDashboard();
  } catch (error) {
    actionStatus.textContent = error?.message || "Collect failed";
    await loadDashboard();
  } finally {
    collectNowButton.disabled = false;
    setTimeout(() => {
      actionStatus.textContent = "";
    }, 5000);
  }
});

flushHistoryButton.addEventListener("click", async () => {
  const password = window.prompt("Enter the flush password to delete stored history and snapshots.");
  if (!password) {
    return;
  }

  const confirmed = window.confirm("This will permanently delete all stored readings and generated snapshots. Continue?");
  if (!confirmed) {
    return;
  }

  flushHistoryButton.disabled = true;
  actionStatus.textContent = "Flushing stored history...";

  try {
    const response = await fetch("/api/admin/flush", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ password }),
    });
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.detail || "Flush failed");
    }

    actionStatus.textContent = `Flushed ${payload.deleted_readings} readings`;
    await loadDashboard();
  } catch (error) {
    actionStatus.textContent = error?.message || "Flush failed";
  } finally {
    flushHistoryButton.disabled = false;
    setTimeout(() => {
      actionStatus.textContent = "";
    }, 5000);
  }
});

loadDashboard().catch((error) => {
  actionStatus.textContent = error.message;
});

setInterval(() => {
  loadDashboard().catch(() => {});
}, 60000);
