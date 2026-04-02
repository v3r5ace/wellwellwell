const levelValue = document.getElementById("level-value");
const levelCaption = document.getElementById("level-caption");
const gallonsRemaining = document.getElementById("gallons-remaining");
const tankFill = document.getElementById("tank-fill");
const readingCount = document.getElementById("reading-count");
const avgLevel = document.getElementById("avg-level");
const levelRange = document.getElementById("level-range");
const avgConfidence = document.getElementById("avg-confidence");
const latestImage = document.getElementById("latest-image");
const latestMeta = document.getElementById("latest-meta");
const chart = document.getElementById("history-chart");
const readingsBody = document.getElementById("readings-body");
const collectNowButton = document.getElementById("collect-now");
const flushHistoryButton = document.getElementById("flush-history");
const bottomActions = document.getElementById("bottom-actions");
const actionStatus = document.getElementById("action-status");

const readingModal = document.getElementById("reading-modal");
const modalClose = document.getElementById("modal-close");
const modalCropImage = document.getElementById("modal-crop-image");
const modalDebugImage = document.getElementById("modal-debug-image");
const modalMeta = document.getElementById("modal-meta");
const modalActions = document.getElementById("modal-actions");
const modalDelete = document.getElementById("modal-delete");

let flushEnabled = false;
let activeReadingId = null;

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
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

function setCurrentLevel(latest) {
  if (!latest) {
    levelValue.textContent = "--";
    levelCaption.textContent = "No reading yet";
    gallonsRemaining.textContent = "-- gallons remaining";
    tankFill.style.height = "0%";
    latestImage.removeAttribute("src");
    latestMeta.textContent = "Waiting for a reading";
    return;
  }

  levelValue.textContent = formatPercent(latest.percent_full);
  levelCaption.textContent = `${latest.marker_found ? "Marker found" : "Marker missing"} • ${dateFormatter.format(new Date(latest.captured_at))}`;
  gallonsRemaining.textContent = `${formatGallons(latest.gallons_remaining)} remaining`;
  tankFill.style.height = `${latest.percent_full ?? 0}%`;

  if (latest.debug_image_url || latest.crop_image_url) {
    latestImage.src = latest.debug_image_url || latest.crop_image_url;
    latestMeta.textContent = `Confidence ${formatConfidence(latest.confidence)} • Y ${latest.marker_center_y == null ? "--" : latest.marker_center_y.toFixed(1)}`;
  } else {
    latestImage.removeAttribute("src");
    latestMeta.textContent = "No crop image available";
  }
}

function setSummary(summary) {
  readingCount.textContent = String(summary.reading_count ?? 0);
  avgLevel.textContent = formatPercent(summary.avg_percent_full);
  if (summary.min_percent_full == null || summary.max_percent_full == null) {
    levelRange.textContent = "--";
  } else {
    levelRange.textContent = `${summary.min_percent_full.toFixed(1)}% - ${summary.max_percent_full.toFixed(1)}%`;
  }
  avgConfidence.textContent = formatConfidence(summary.avg_confidence);
}

function renderChart(readings) {
  chart.innerHTML = "";

  const points = readings
    .filter((reading) => reading.percent_full != null)
    .reverse();

  if (points.length < 2) {
    const message = document.createElementNS("http://www.w3.org/2000/svg", "text");
    message.setAttribute("x", "50%");
    message.setAttribute("y", "50%");
    message.setAttribute("text-anchor", "middle");
    message.setAttribute("fill", "#5d6c63");
    message.textContent = "Not enough readings yet";
    chart.appendChild(message);
    return;
  }

  const width = 900;
  const height = 280;
  const padding = 28;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;

  for (let index = 0; index <= 4; index += 1) {
    const y = padding + ((usableHeight / 4) * index);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("x1", String(padding));
    line.setAttribute("x2", String(width - padding));
    line.setAttribute("y1", String(y));
    line.setAttribute("y2", String(y));
    line.setAttribute("stroke", "rgba(33, 48, 39, 0.12)");
    chart.appendChild(line);
  }

  const pathCommands = points.map((reading, index) => {
    const x = padding + ((usableWidth / (points.length - 1)) * index);
    const y = padding + usableHeight - ((reading.percent_full / 100) * usableHeight);
    return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  });

  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", pathCommands.join(" "));
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "#c2185b");
  path.setAttribute("stroke-width", "4");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  chart.appendChild(path);

  const latest = points.at(-1);
  if (latest) {
    const x = width - padding;
    const y = padding + usableHeight - ((latest.percent_full / 100) * usableHeight);
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    marker.setAttribute("cx", String(x));
    marker.setAttribute("cy", String(y));
    marker.setAttribute("r", "6");
    marker.setAttribute("fill", "#f48fb1");
    marker.setAttribute("stroke", "#880e4f");
    marker.setAttribute("stroke-width", "3");
    chart.appendChild(marker);
  }
}

function renderTable(readings) {
  readingsBody.innerHTML = "";

  if (!readings.length) {
    const row = document.createElement("tr");
    row.innerHTML = '<td colspan="7" class="empty">No readings yet</td>';
    readingsBody.appendChild(row);
    return;
  }

  for (const reading of readings.slice(0, 20)) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${dateFormatter.format(new Date(reading.captured_at))}</td>
      <td>${formatPercent(reading.percent_full)}</td>
      <td>${formatGallons(reading.gallons_remaining)}</td>
      <td>${reading.marker_center_y == null ? "--" : reading.marker_center_y.toFixed(1)}</td>
      <td>${formatConfidence(reading.confidence)}</td>
      <td>${reading.source_kind}</td>
      <td>${reading.notes}</td>
    `;
    row.addEventListener("click", () => openReadingModal(reading));
    readingsBody.appendChild(row);
  }
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

async function loadDashboard() {
  const [statusResponse, readingsResponse] = await Promise.all([
    fetch("/api/status"),
    fetch("/api/readings?limit=96"),
  ]);

  if (!statusResponse.ok || !readingsResponse.ok) {
    throw new Error("Unable to load dashboard data");
  }

  const status = await statusResponse.json();
  const readings = await readingsResponse.json();

  flushEnabled = !!status.admin?.flush_enabled;
  bottomActions.hidden = !flushEnabled;
  setCurrentLevel(status.latest);
  setSummary(status.summary);
  renderChart(readings.items);
  renderTable(readings.items);
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
