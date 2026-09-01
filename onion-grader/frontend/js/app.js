/* ============================================================
   Onion Quality Analyzer — front-end logic (full prototype)
   Tabs: Analyze (single) · Batch (URS %) · Test (evaluation)
   The UI displays ONLY what the server measured — it never
   invents scores, grades or confidences.
   ============================================================ */
"use strict";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ---------------- element refs ---------------- */
const els = {
  tabs: document.querySelectorAll(".tab"),
  views: { home: $("view-home"), preview: $("view-preview"),
           processing: $("view-processing"), result: $("view-result") },
  banner: $("banner"),
  btnTakePhoto: $("btn-take-photo"), btnUpload: $("btn-upload"),
  fileInput: $("file-input"), cameraInput: $("camera-input"),
  cameraModal: $("camera-modal"), cameraVideo: $("camera-video"),
  btnCapture: $("btn-capture"), btnCameraClose: $("btn-camera-close"),
  previewImg: $("preview-img"), fileMeta: $("file-meta"),
  btnRetake: $("btn-retake"), btnAnalyze: $("btn-analyze"),
  processingStatus: $("processing-status"),
  resultCard: $("result-card"), btnStartOver: $("btn-start-over"),
  btnBatchUpload: $("btn-batch-upload"), batchInput: $("batch-input"),
  batchProgress: $("batch-progress"), batchProgressText: $("batch-progress-text"),
  batchProgressBar: $("batch-progress-bar"), batchDashboard: $("batch-dashboard"),
  evalFile: $("eval-file"), evalActual: $("eval-actual"), btnEvalRun: $("btn-eval-run"),
  evalTableHolder: $("eval-table-holder"), btnEvalMetrics: $("btn-eval-metrics"),
  evalMetricsHolder: $("eval-metrics-holder"),
  btnEvalDataset: $("btn-eval-dataset"), evalDatasetHolder: $("eval-dataset-holder"),
};

const MAX_BYTES = 8 * 1024 * 1024;
const GRADE_COLORS = { A: "#15803d", B: "#0e7490", C: "#b45309", URS: "#b91c1c" };

let currentFile = null, objectUrl = null, cameraStream = null;
let lastResult = null;
let evalRows = [];

/* ---------------- tabs ---------------- */
els.tabs.forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("is-active", t === tab));
  document.querySelectorAll(".tabpanel").forEach((p) =>
    p.classList.toggle("is-active", p.id === `tab-${tab.dataset.tab}`));
}));

/* ---------------- banner / views ---------------- */
function showBanner(msg, kind = "error", ms = 5000) {
  els.banner.textContent = msg;
  els.banner.className = `banner ${kind}`;
  els.banner.hidden = false;
  clearTimeout(showBanner._t);
  showBanner._t = setTimeout(() => (els.banner.hidden = true), ms);
}
function showView(name) {
  Object.entries(els.views).forEach(([k, el]) => el.classList.toggle("is-active", k === name));
  window.scrollTo({ top: 0 });
}

/* ---------------- image picking (single) ---------------- */
els.btnUpload.addEventListener("click", () => els.fileInput.click());
els.fileInput.addEventListener("change", () => handlePicked(els.fileInput.files[0]));

els.btnTakePhoto.addEventListener("click", async () => {
  if (!navigator.mediaDevices?.getUserMedia) return els.cameraInput.click();
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" }, audio: false });
    els.cameraVideo.srcObject = cameraStream;
    els.cameraModal.hidden = false;
  } catch { els.cameraInput.click(); }   // fallback: native camera input
});
els.cameraInput.addEventListener("change", () => handlePicked(els.cameraInput.files[0]));

function closeLiveCamera() {
  cameraStream?.getTracks().forEach((t) => t.stop());
  cameraStream = null;
  els.cameraVideo.srcObject = null;
  els.cameraModal.hidden = true;
}
els.btnCameraClose.addEventListener("click", closeLiveCamera);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !els.cameraModal.hidden) closeLiveCamera();
});

els.btnCapture.addEventListener("click", () => {
  const v = els.cameraVideo;
  if (!v.videoWidth) return;
  const c = document.createElement("canvas");
  c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext("2d").drawImage(v, 0, 0);
  c.toBlob((blob) => {
    closeLiveCamera();
    handlePicked(new File([blob], "onion-capture.jpg", { type: "image/jpeg" }));
  }, "image/jpeg", 0.92);
});

function handlePicked(file) {
  els.fileInput.value = ""; els.cameraInput.value = "";
  if (!file) return;
  if (!/\.(jpe?g|png)$/i.test(file.name) || !["image/jpeg", "image/png"].includes(file.type))
    return showBanner("Please choose a JPG or PNG image.");
  if (file.size > MAX_BYTES)
    return showBanner(`Image too large (${(file.size / 1048576).toFixed(1)} MB). Max 8 MB.`);
  currentFile = file;
  if (objectUrl) URL.revokeObjectURL(objectUrl);
  objectUrl = URL.createObjectURL(file);
  els.previewImg.src = objectUrl;
  els.fileMeta.textContent = `${file.name} · ${(file.size / 1024).toFixed(0)} KB`;
  showView("preview");
}

els.btnRetake.addEventListener("click", () => showView("home"));
els.btnStartOver.addEventListener("click", () => showView("home"));

/* ---------------- ANALYZE ---------------- */
els.btnAnalyze.addEventListener("click", async () => {
  if (!currentFile) return;
  showView("processing");
  setProcessingStatus("Uploading image…");
  const steps = ["Detecting onion (segmentation)…", "Measuring features…",
                 "Checking defects…", "Scoring & grading…"];
  let i = 0;
  const tick = setInterval(() => { if (i < steps.length) setProcessingStatus(steps[i++]); }, 500);
  try {
    const form = new FormData();
    form.append("file", currentFile, currentFile.name);
    const res = await fetch("/api/analyze", { method: "POST", body: form });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || `Server error (${res.status})`);
    lastResult = body;
    els.resultCard.innerHTML = renderResult(body);
    showView("result");
  } catch (err) {
    showBanner(err.message || "Could not reach the analysis server.");
    showView("preview");
  } finally { clearInterval(tick); }
});

function setProcessingStatus(text) { els.processingStatus.textContent = text; }

/* ---------------- result rendering ---------------- */
function renderResult(b) {
  const det = b.detection || {};

  /* no onion detected → honest guidance card */
  if (!det.found) {
    return `
      <div class="card">
        <p class="result-heading"><span class="result-warn">⚠</span> No onion detected</p>
        <p>${esc(det.reason || "The onion could not be separated from the background.")}</p>
        <div class="notice">No score, grade or defects are reported — the system does not
        guess when detection fails.</div>
      </div>`;
  }

  const score = b.quality_score.score;
  const g = b.grade || {};
  const conf = (b.analysis_confidence || {}).value ?? 0;
  const gaugeCol = `conic-gradient(#9a3412 ${score * 3.6}deg, #f3e5d7 0deg)`;

  const chips = [b.image.format, `${b.image.width}×${b.image.height} px`,
                 `${b.image.megapixels} MP`].map((c) => `<span class="chip">${esc(c)}</span>`).join("");

  const defectsHtml = (b.defects || []).map((d) => {
    if (d.status === "detected") {
      const conf = d.fused_confidence ?? d.confidence ?? 0;
      const mlTag = d.ml_supports === true
        ? ' <span class="ml-tag ok">ML ✓</span>'
        : d.ml_supports === false
          ? ' <span class="ml-tag bad">ML ✗</span>' : "";
      return `<div class="defect detected">
        <div class="d-title"><span>✗ ${esc(d.label)}${mlTag}</span>
          <span><span class="sev ${esc(d.severity)}">${esc(d.severity)}</span></span></div>
        <div class="d-ev"><strong>Confidence: ${Math.round(conf * 100)}%</strong> · ${esc(d.evidence)}</div>
      </div>`;
    }
    if (d.status === "insufficient_evidence") {
      return `<div class="defect insuff">
        <div class="d-title"><span>ℹ ${esc(d.label)}</span></div>
        <div class="d-ev">Insufficient visual evidence — ${esc(d.evidence)}</div>
      </div>`;
    }
    return `<div class="defect ok">
      <div class="d-title"><span>✓ No ${esc(d.label.toLowerCase())}</span></div>
      <div class="d-ev">${esc(d.evidence)}</div>
    </div>`;
  }).join("");

  const reasonsHtml = ((b.quality_score || {}).reasons || [])
    .map((r) => `<div class="reason ${esc(r.level)}">${esc(r.text)}</div>`).join("");

  const f = b.features || {};
  const kv = `
    <table class="kv">
      <tr><td>Equivalent diameter</td><td>${esc(f.equivalent_diameter_px)} px <span class="muted small">(px, not mm)</span></td></tr>
      <tr><td>Onion area</td><td>${esc(f.area_px)} px² (${Math.round((f.area_fraction || 0) * 100)}% of photo)</td></tr>
      <tr><td>Shape (circularity)</td><td>${esc(f.circularity)}</td></tr>
      <tr><td>Colour mean hue</td><td>${esc(f.hue_circ_mean_deg)}° · spread ${esc(f.hue_circular_std_deg)}°</td></tr>
      <tr><td>Detection method</td><td>${esc(det.method)}</td></tr>
      <tr><td>Analysis confidence</td><td><strong>${Math.round(conf * 100)}%</strong></td></tr>
    </table>`;

  return `
    <div class="card">
      <div class="score-wrap">
        <div class="gauge" style="background:${gaugeCol}">
          <span class="val">${score}<small style="font-size:.8rem">/100</small></span>
        </div>
        <div>
          <span class="grade-badge grade-${esc(g.grade)}">${esc(g.grade)}</span>
          <p class="small" style="margin:8px 0 0">${esc(g.recommendation || "")}</p>
        </div>
      </div>
      ${g.basis ? `<p class="small muted" style="margin-top:10px">Basis: ${esc(g.basis)}</p>` : ""}
      <div style="margin-top:10px">${chips}</div>
      <div class="annotated-frame">
        <img src="data:image/jpeg;base64,${det.annotated_image_b64}" alt="Analysed onion with annotations" />
      </div>
      <p class="small muted center">Green = detected onion · amber box = bounding box · red = defect regions</p>

      <p class="section-label">Grade probabilities</p>
      ${renderGradeProbabilities(b.grade_probabilities, g.grade)}

      <p class="section-label">Defects found</p>
      ${defectsHtml}

      <p class="section-label">Why this score</p>
      ${reasonsHtml}

      <p class="section-label">Measurements</p>
      ${kv}

      <p class="section-label">AI engine</p>
      ${renderModelBlock(b.model)}

      <a class="btn btn-primary" style="text-decoration:none;text-align:center;margin-top:16px"
         href="/api/report/${esc(b.analysis_id)}.pdf" target="_blank" rel="noopener">📄 View detailed report (PDF)</a>

      <div class="disclaimer">
        ${b.disclaimers.map((d) => `• ${esc(d)}`).join("<br>")}
      </div>
    </div>`;
}

function renderGradeProbabilities(gp, pointGrade) {
  if (!gp || !gp.probabilities) {
    return `<div class="notice">Grade probabilities not computed.</div>`;
  }
  const rows = ["A", "B", "C", "URS"].map((gr) => {
    const p = (gp.probabilities[gr] ?? 0) * 100;
    return `<div class="dist-row">
      <div class="dist-label">Grade ${esc(gr)}${gr === pointGrade ? " ◂" : ""}</div>
      <div class="dist-track"><div class="dist-fill" style="width:${Math.max(p, 2)}%;background:${GRADE_COLORS[gr]}">${p >= 12 ? p.toFixed(0) + "%" : ""}</div></div>
      <div class="dist-pct">${p.toFixed(0)}%</div>
    </div>`;
  }).join("");
  return `${rows}<p class="muted small" style="margin:6px 0 0">${esc(gp.method || "")}</p>`;
}

function renderModelBlock(m) {
  if (!m) return "";
  const agree = m.ensemble_agreement === "rules_and_model_agree"
    ? '<span class="pill-ok">rules & model agree</span>'
    : m.ensemble_agreement === "rules_and_model_disagree"
      ? '<span class="pill-bad">streams disagree — reduced confidence</span>'
      : '<span class="pill-ok">rule engine</span>';
  const ml = m.ml_predictions;
  const preds = ml
    ? ml.predictions.slice(0, 3).map((p) =>
        `<span class="chip">${esc(p.label)} ${Math.round(p.probability * 100)}%</span>`).join("")
    : "";
  return `<table class="kv">
    <tr><td>Engine</td><td><strong>${esc(m.type)}</strong> · ${agree}</td></tr>
    ${m.trained_ml_loaded ? `
      <tr><td>Model trained on</td><td>${esc(m.trained_on)} images</td></tr>
      <tr><td>Validation accuracy</td><td>${esc(String(m.validation_accuracy_on_training_dist))} <span class="muted small">(on ${esc(m.trained_on)} — field validation pending)</span></td></tr>
      <tr><td>ML class estimate</td><td>${preds || "—"}</td></tr>` : `
      <tr><td>ML model</td><td>not loaded — rules only (honestly reported)</td></tr>`}
  </table>`;
}

/* ---------------- BATCH ---------------- */
els.btnBatchUpload.addEventListener("click", () => els.batchInput.click());
els.batchInput.addEventListener("change", async () => {
  const files = Array.from(els.batchInput.files || []);
  els.batchInput.value = "";
  if (!files.length) return;
  if (files.length > 25) return showBanner("Maximum 25 images per batch.");

  els.batchProgress.hidden = false;
  els.batchDashboard.innerHTML = "";
  const form = new FormData();
  files.forEach((f) => form.append("files", f, f.name));

  // upload with progress
  await new Promise((resolve) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/batch");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const p = Math.round((e.loaded / e.total) * 90);
        els.batchProgressBar.style.width = p + "%";
        els.batchProgressText.textContent = `Uploading ${files.length} images… ${p}%`;
      }
    };
    xhr.onload = () => {
      els.batchProgressBar.style.width = "100%";
      els.batchProgressText.textContent = "Analysis complete";
      let body = {};
      try { body = JSON.parse(xhr.responseText); } catch {}
      if (xhr.status !== 200) {
        showBanner(body.detail || `Batch failed (${xhr.status})`);
      } else {
        els.batchDashboard.innerHTML = renderBatch(body, files.length);
      }
      resolve();
    };
    xhr.onerror = () => { showBanner("Network error during batch upload."); };
    xhr.send(form);
  });
  setTimeout(() => (els.batchProgress.hidden = true), 800);
});

function renderBatch(b, totalPicked) {
  const d = b.distribution || {};
  const rows = ["A", "B", "C", "URS"].map((g) => {
    const pct = d[g]?.pct ?? 0, cnt = d[g]?.count ?? 0;
    return `<div class="dist-row">
      <div class="dist-label">Grade ${esc(g)}</div>
      <div class="dist-track"><div class="dist-fill" style="width:${Math.max(pct, 2)}%;background:${GRADE_COLORS[g]}">${cnt}</div></div>
      <div class="dist-pct">${pct.toFixed(1)}%</div>
    </div>`;
  }).join("");

  const items = (b.items || []).map((it) => {
    const status = !it.ok ? `<span class="pill-bad">error</span>`
      : !it.found ? `<span class="pill-bad">not detected</span>`
      : `Grade <b>${esc(it.grade)}</b> · ${it.quality_score ?? "—"}/100`;
    return `<tr>
      <td>${it.index}</td><td>${esc(it.filename)}</td><td>${status}</td>
      <td>${it.defects_detected?.length ? esc(it.defects_detected.join(", ")) : "—"}</td>
    </tr>`;
  }).join("");

  return `
    <div class="card">
      <p class="result-heading"><span class="result-ok">✓</span> Batch analysed</p>
      <table class="kv">
        <tr><td>Total onions analysed</td><td><strong>${b.onions_found}</strong> (of ${totalPicked} images)</td></tr>
        <tr><td>Average quality score</td><td><strong>${b.avg_quality_score ?? "—"}/100</strong></td></tr>
        <tr><td>Not detected / errors</td><td>${b.undetermined + (totalPicked - b.analysed_ok)}</td></tr>
      </table>
      <p class="section-label">Grade distribution</p>
      ${rows}
      <p class="notice">${esc(b.note || "")}</p>
      <p class="section-label">Per-onion results</p>
      <div style="overflow-x:auto"><table class="data">
        <tr><th>#</th><th>File</th><th>Result</th><th>Defects</th></tr>${items}
      </table></div>
      <a class="btn btn-primary" style="text-decoration:none;text-align:center;margin-top:16px"
         href="${esc(b.report_url)}" target="_blank" rel="noopener">📄 Download batch report (PDF)</a>
      <div class="disclaimer">${(b.disclaimers || []).map((x) => `• ${esc(x)}`).join("<br>")}</div>
    </div>`;
}

/* ---------------- EVALUATION (Test tab) ---------------- */
els.btnEvalRun.addEventListener("click", async () => {
  const file = els.evalFile.files[0];
  const actual = els.evalActual.value;
  if (!file) return showBanner("Choose an onion image to test.");
  els.btnEvalRun.disabled = true;
  els.btnEvalRun.textContent = "Testing…";
  try {
    const form = new FormData();
    form.append("file", file, file.name);
    form.append("actual", actual);
    const res = await fetch("/api/evaluate", { method: "POST", body: form });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || `Error (${res.status})`);
    evalRows.unshift(body);
    renderEvalTable();
  } catch (err) {
    showBanner(err.message || "Test failed.");
  } finally {
    els.btnEvalRun.disabled = false;
    els.btnEvalRun.textContent = "▶ Run test";
    els.evalFile.value = "";
  }
});

function renderEvalTable() {
  if (!evalRows.length) { els.evalTableHolder.innerHTML = ""; return; }
  const rows = evalRows.map((r) => `<tr>
      <td>${esc(r.filename)}</td><td>${esc(r.actual)}</td><td>${esc(r.predicted)}</td>
      <td>${Math.round((r.confidence || 0) * 100)}%</td>
      <td>${r.correct ? '<span class="pill-ok">correct</span>' : '<span class="pill-bad">incorrect</span>'}</td>
      <td>${r.grade ?? "—"}</td>
    </tr>`).join("");
  els.evalTableHolder.innerHTML = `
    <div class="card">
      <p class="section-label">Test results (this session)</p>
      <div style="overflow-x:auto"><table class="data">
        <tr><th>File</th><th>Actual</th><th>Predicted</th><th>Conf.</th><th>Result</th><th>Grade</th></tr>
        ${rows}</table></div>
    </div>`;
}

els.btnEvalMetrics.addEventListener("click", async () => {
  els.btnEvalMetrics.disabled = true;
  try {
    const res = await fetch("/api/evaluate/metrics");
    const body = await res.json();
    els.evalMetricsHolder.innerHTML = renderMetrics(body);
  } catch { showBanner("Could not load metrics."); }
  finally { els.btnEvalMetrics.disabled = false; }
});

/* ---------------- HELD-OUT TEST SET (live demo) ---------------- */
els.btnEvalDataset.addEventListener("click", async () => {
  const btn = els.btnEvalDataset;
  btn.disabled = true;
  btn.textContent = "⏳ Running held-out test set through the full pipeline…";
  els.evalDatasetHolder.innerHTML =
    `<div class="card"><div class="spinner"></div>
     <p class="center small muted">Segmenting → measuring → ensemble-predicting every test image.
     This measures the number LIVE — nothing is pre-recorded.</p></div>`;
  try {
    const res = await fetch("/api/evaluate/dataset-test?dataset=synthetic_v1&limit_per_class=15", {
      method: "POST",
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || `Error (${res.status})`);
    els.evalDatasetHolder.innerHTML = renderDatasetTest(body);
  } catch (err) {
    els.evalDatasetHolder.innerHTML =
      `<div class="card"><div class="notice">${esc(err.message)}</div></div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "🏁 Run held-out test set (live)";
  }
});

function renderDatasetTest(b) {
  const m = b.metrics;
  const accPct = (m.accuracy * 100).toFixed(1);
  const perfect = m.accuracy >= 0.999;
  const cm = m.confusion_matrix;
  const cmHead = `<tr><th>actual ↓ / pred →</th>${cm.labels.map((l) => `<th>${esc(l)}</th>`).join("")}</tr>`;
  const cmRows = cm.labels.map((lbl, i) =>
    `<tr><td><b>${esc(lbl)}</b></td>${cm.matrix[i].map((v, j) =>
      `<td${i === j && v > 0 ? ' style="background:#dcfce7;font-weight:700"' : (v > 0 ? ' style="background:#fee2e2"' : "")}>${v}</td>`).join("")}</tr>`).join("");
  const per = (m.per_class || []).map((c) => `<tr>
      <td>${esc(c.label)}</td><td>${c.precision}</td><td>${c.recall}</td><td>${c.f1}</td><td>${c.support}</td></tr>`).join("");
  return `<div class="card">
    <p class="result-heading"><span class="result-ok">✓</span> Held-out test set — measured live</p>
    <div class="score-wrap">
      <div class="gauge" style="background:conic-gradient(#15803d ${m.accuracy*360}deg, #f3e5d7 0deg)">
        <span class="val">${accPct}<small style="font-size:.8rem">%</small></span>
      </div>
      <div>
        <p style="margin:0;font-weight:800;font-size:1.1rem">
          ${b.n_correct}/${b.n_images} correct${perfect ? " — perfect score on this set" : ""}</p>
        <p class="small muted" style="margin:4px 0 0">dataset: ${esc(b.dataset)} ·
          skipped: ${b.skipped} · weighted F1: ${m.weighted_f1}</p>
      </div>
    </div>
    <div class="notice">${esc(b.note)}</div>
    <p class="small muted" style="margin-top:8px">${esc(b.pipeline)}. Model trained on
      ${esc(String(b.model_trained_on))} (val acc ${esc(String(b.model_val_accuracy))} on that distribution).</p>
    <p class="section-label">Confusion matrix</p>
    <div style="overflow-x:auto"><table class="data">${cmHead}${cmRows}</table></div>
    <p class="section-label">Per class</p>
    <div style="overflow-x:auto"><table class="data">
      <tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>n</th></tr>${per}</table></div>
  </div>`;
}

/* ---------------- SCAN (multi-onion pile) ---------------- */
const scanEls = {
  btnPhoto: $("btn-scan-photo"), btnUpload: $("btn-scan-upload"),
  file: $("scan-file"), camera: $("scan-camera"),
  previewWrap: $("scan-preview-wrap"), previewImg: $("scan-preview-img"),
  btnRetake: $("btn-scan-retake"), btnRun: $("btn-scan-run"),
  progress: $("scan-progress"), progressText: $("scan-progress-text"),
  result: $("scan-result"),
};
let scanFile = null, scanUrl = null;

scanEls.btnUpload.addEventListener("click", () => scanEls.file.click());
scanEls.btnPhoto.addEventListener("click", () => scanEls.camera.click());
scanEls.file.addEventListener("change", () => scanPicked(scanEls.file.files[0]));
scanEls.camera.addEventListener("change", () => scanPicked(scanEls.camera.files[0]));
scanEls.btnRetake.addEventListener("click", () => {
  scanEls.previewWrap.hidden = true;
  scanEls.result.innerHTML = "";
});

function scanPicked(file) {
  scanEls.file.value = ""; scanEls.camera.value = "";
  if (!file) return;
  if (!/\.(jpe?g|png)$/i.test(file.name) || !["image/jpeg", "image/png"].includes(file.type))
    return showBanner("Please choose a JPG or PNG photo.");
  if (file.size > MAX_BYTES) return showBanner("Photo too large. Max 8 MB.");
  scanFile = file;
  if (scanUrl) URL.revokeObjectURL(scanUrl);
  scanUrl = URL.createObjectURL(file);
  scanEls.previewImg.src = scanUrl;
  scanEls.previewWrap.hidden = false;
  scanEls.result.innerHTML = "";
}

scanEls.btnRun.addEventListener("click", async () => {
  if (!scanFile) return;
  scanEls.previewWrap.hidden = true;
  scanEls.progress.hidden = false;
  const steps = ["Detecting onions (watershed segmentation)…",
                 "Measuring each onion…", "AI ensemble per onion…",
                 "Colour-coding and reporting…"];
  let si = 0;
  scanEls.progressText.textContent = steps[0];
  const tick = setInterval(() => {
    si = (si + 1) % steps.length; scanEls.progressText.textContent = steps[si];
  }, 700);
  try {
    const form = new FormData();
    form.append("file", scanFile, scanFile.name);
    const res = await fetch("/api/scan", { method: "POST", body: form });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(body.detail || `Server error (${res.status})`);
    scanEls.result.innerHTML = renderScan(body);
    window.scrollTo({ top: 0 });
  } catch (err) {
    showBanner(err.message || "Scan failed.");
    scanEls.previewWrap.hidden = false;
  } finally {
    clearInterval(tick);
    scanEls.progress.hidden = true;
  }
});

function renderScan(b) {
  if (!b.onions_found) {
    return `<div class="card"><div class="notice">No onions detected. Retake from ~50 cm
      above the pile on a contrasting surface.</div></div>`;
  }
  const hexFor = (cls) => ((b.legend || []).find((l) => l.label === cls) || {}).hex || "#9ca3af";
  const legend = (b.legend || []).map((l) =>
    `<span class="legend-chip"><span class="dot" style="background:${esc(l.hex)}"></span>
     ${esc(l.label)} × ${l.count}</span>`).join("");
  const bars = ["A", "B", "C", "URS"].map((g) => {
    const pct = b.distribution[g]?.pct ?? 0, cnt = b.distribution[g]?.count ?? 0;
    return `<div class="dist-row">
      <div class="dist-label">Grade ${esc(g)}</div>
      <div class="dist-track"><div class="dist-fill" style="width:${Math.max(pct, 2)}%;background:${GRADE_COLORS[g]}">${cnt}</div></div>
      <div class="dist-pct">${pct.toFixed(1)}%</div></div>`;
  }).join("");
  const rows = (b.onions || []).map((o) => `<tr>
      <td>${o.index}</td>
      <td><span class="dot" style="display:inline-block;background:${esc(hexFor(o.class))}"></span> ${esc(o.class)}</td>
      <td>${Math.round((o.confidence || 0) * 100)}%</td>
      <td>${o.quality_score}</td>
      <td><b>${esc(o.grade)}</b></td>
      <td>${o.defects?.length ? esc(o.defects.join(", ")) : "—"}</td></tr>`).join("");
  return `<div class="card">
    <p class="result-heading"><span class="result-ok">✓</span> ${b.onions_found} onions detected
      <span class="muted small">· ${esc(b.method)}</span></p>
    <div class="scan-viewer">
      <img src="data:image/jpeg;base64,${b.annotated_image_b64}" alt="Colour-coded onion scan" />
    </div>
    <div class="legend-row">${legend}</div>
    <table class="kv" style="margin-top:8px">
      <tr><td>Average quality score</td><td><strong>${b.avg_quality_score ?? "—"}/100</strong></td></tr>
    </table>
    <p class="section-label">Grade distribution (share of detected onions)</p>
    ${bars}
    <div class="notice">${esc(b.note || "")}</div>
    <p class="section-label">Per-onion results</p>
    <div class="scroll-box"><table class="data">
      <tr><th>#</th><th>Class</th><th>Conf.</th><th>Score</th><th>Grade</th><th>Defects</th></tr>
      ${rows}</table></div>
    <a class="btn btn-primary" style="text-decoration:none;text-align:center;margin-top:16px"
       href="${esc(b.report_url)}" target="_blank" rel="noopener">📄 Download scan report (PDF)</a>
    <div class="disclaimer">${(b.disclaimers || []).map((d) => `• ${esc(d)}`).join("<br>")}</div>
  </div>`;
}

function renderMetrics(body) {
  if (!body.metrics) {
    return `<div class="card"><div class="notice">${esc(body.note || "")}</div></div>`;
  }
  const m = body.metrics;
  let cm = "";
  if (m.confusion_matrix) {
    const head = `<tr><th>actual ↓ / pred →</th>${m.confusion_matrix.labels.map((l) => `<th>${esc(l)}</th>`).join("")}</tr>`;
    const rows = m.confusion_matrix.labels.map((lbl, i) =>
      `<tr><td><b>${esc(lbl)}</b></td>${m.confusion_matrix.matrix[i].map((v) => `<td>${v}</td>`).join("")}</tr>`).join("");
    cm = `<p class="section-label">Confusion matrix</p>
          <div style="overflow-x:auto"><table class="data">${head}${rows}</table></div>`;
  }
  const per = (m.per_class || []).map((c) => `<tr>
      <td>${esc(c.label)}</td><td>${c.precision}</td><td>${c.recall}</td><td>${c.f1}</td><td>${c.support}</td>
    </tr>`).join("");
  return `<div class="card">
    <p class="section-label">Measured metrics (n = ${body.n} tested images)</p>
    <table class="kv">
      <tr><td>Accuracy</td><td><strong>${(m.accuracy * 100).toFixed(1)}%</strong></td></tr>
      <tr><td>Weighted precision</td><td>${m.weighted_precision ?? "—"}</td></tr>
      <tr><td>Weighted recall</td><td>${m.weighted_recall ?? "—"}</td></tr>
      <tr><td>Weighted F1</td><td>${m.weighted_f1 ?? "—"}</td></tr>
    </table>
    ${per ? `<p class="section-label">Per class</p>
      <div style="overflow-x:auto"><table class="data">
      <tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>n</th></tr>${per}</table></div>` : ""}
    ${cm}
    <div class="notice">${esc(m.note || "")}</div>
  </div>`;
}
