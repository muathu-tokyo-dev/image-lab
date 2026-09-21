const state = {
  imageId: null,
  technique: "hsv",
  currentPreviewUrl: null,
  processingController: null,
  requestSeq: 0,
};

const $ = (id) => document.getElementById(id);
const fileInput = $("fileInput");
const beforeImage = $("beforeImage");
const afterImage = $("afterImage");
const exportBtn = $("exportBtn");
const resetBtn = $("resetBtn");
const loader = $("loader");
const processingText = $("processingText");
const statusDot = $("statusDot");
const imageMeta = $("imageMeta");
const histogramCanvas = $("histogramCanvas");

const sliderIds = ["hue", "saturation", "value", "blacks", "shadows", "midtones", "highlights", "whites"];

function payload() {
  return {
    image_id: state.imageId,
    technique: state.technique,
    hsv: {
      hue: Number($("hue").value),
      saturation: Number($("saturation").value),
      value: Number($("value").value),
    },
    histogram: {
      blacks: Number($("blacks").value),
      shadows: Number($("shadows").value),
      midtones: Number($("midtones").value),
      highlights: Number($("highlights").value),
      whites: Number($("whites").value),
    },
  };
}

function refreshOutputs() {
  $("hueOut").textContent = `${$("hue").value}°`;
  ["saturation", "value", "blacks", "shadows", "midtones", "highlights", "whites"].forEach(id => {
    const v = Number($(id).value);
    $(`${id}Out`).textContent = v > 0 ? `+${v}` : `${v}`;
  });
}

function resetSliders() {
  sliderIds.forEach(id => $(id).value = 0);
  refreshOutputs();
}

function setTechnique(technique) {
  state.technique = technique;
  document.querySelectorAll(".tech-card").forEach(btn => btn.classList.toggle("active", btn.dataset.technique === technique));
  $("hsvControls").classList.toggle("active", technique === "hsv");
  $("histogramControls").classList.toggle("active", technique === "histogram");
  if (state.imageId) scheduleProcess(0);
}

document.querySelectorAll(".tech-card").forEach(btn => btn.addEventListener("click", () => setTechnique(btn.dataset.technique)));

fileInput.addEventListener("change", async () => {
  const file = fileInput.files?.[0];
  if (!file) return;

  const form = new FormData();
  form.append("file", file);
  processingText.textContent = "UPLOADING";
  loader.classList.remove("hidden");

  try {
    const res = await fetch("/api/upload", { method: "POST", body: form });
    if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
    const data = await res.json();

    state.imageId = data.image_id;
    resetSliders();

    const original = `${data.original_url}?t=${Date.now()}`;
    beforeImage.src = original;
    afterImage.src = original;
    beforeImage.classList.add("visible");
    afterImage.classList.add("visible");
    $("emptyBefore").classList.add("hidden");
    $("emptyAfter").classList.add("hidden");

    imageMeta.textContent = `${data.width}×${data.height}`;
    exportBtn.disabled = false;
    resetBtn.disabled = false;
    statusDot.classList.add("online");
    processingText.textContent = "READY";

    afterImage.onload = drawHistogram;
  } catch (err) {
    alert(err.message);
    processingText.textContent = "ERROR";
  } finally {
    loader.classList.add("hidden");
    fileInput.value = "";
  }
});

let timer = null;
function scheduleProcess(delay = 90) {
  clearTimeout(timer);
  timer = setTimeout(processRealtime, delay);
}

sliderIds.forEach(id => {
  $(id).addEventListener("input", () => {
    refreshOutputs();
    if (state.imageId) scheduleProcess();
  });
});

async function processRealtime() {
  if (!state.imageId) return;
  const seq = ++state.requestSeq;

  if (state.processingController) state.processingController.abort();
  state.processingController = new AbortController();
  loader.classList.remove("hidden");
  processingText.textContent = "PROCESSING";

  try {
    const res = await fetch("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
      signal: state.processingController.signal,
    });
    if (!res.ok) throw new Error("Processing failed");
    const blob = await res.blob();
    if (seq !== state.requestSeq) return;

    if (state.currentPreviewUrl) URL.revokeObjectURL(state.currentPreviewUrl);
    state.currentPreviewUrl = URL.createObjectURL(blob);
    afterImage.onload = () => {
      drawHistogram();
      loader.classList.add("hidden");
      processingText.textContent = "LIVE";
    };
    afterImage.src = state.currentPreviewUrl;
  } catch (err) {
    if (err.name !== "AbortError") {
      console.error(err);
      processingText.textContent = "ERROR";
      loader.classList.add("hidden");
    }
  }
}

resetBtn.addEventListener("click", () => {
  if (!state.imageId) return;
  if (state.processingController) state.processingController.abort();
  resetSliders();
  const original = `/api/original/${state.imageId}?t=${Date.now()}`;
  afterImage.onload = drawHistogram;
  afterImage.src = original;
  processingText.textContent = "RESET";
});

exportBtn.addEventListener("click", async () => {
  if (!state.imageId) return;
  exportBtn.disabled = true;
  const old = exportBtn.textContent;
  exportBtn.textContent = "EXPORTING...";
  try {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = res.headers.get("content-disposition")?.match(/filename="?([^";]+)"?/)?.[1] || "neon-edit.png";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message);
  } finally {
    exportBtn.textContent = old;
    exportBtn.disabled = false;
  }
});

function drawHistogram() {
  if (!afterImage.complete || !afterImage.naturalWidth) return;

  const c = document.createElement("canvas");
  const w = 420;
  const scale = w / afterImage.naturalWidth;
  c.width = w;
  c.height = Math.max(1, Math.round(afterImage.naturalHeight * scale));
  const cx = c.getContext("2d", { willReadFrequently: true });

  try {
    cx.drawImage(afterImage, 0, 0, c.width, c.height);
    const data = cx.getImageData(0, 0, c.width, c.height).data;
    const bins = new Array(256).fill(0);
    for (let i = 0; i < data.length; i += 4) {
      const lum = Math.max(0, Math.min(255, Math.round(0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2])));
      bins[lum]++;
    }

    const ctx = histogramCanvas.getContext("2d");
    const W = histogramCanvas.width, H = histogramCanvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#080c12";
    ctx.fillRect(0, 0, W, H);

    const max = Math.max(...bins, 1);
    ctx.strokeStyle = "rgba(53,242,255,0.12)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= 4; x++) {
      const px = x * W / 4;
      ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, H); ctx.stroke();
    }

    ctx.beginPath();
    bins.forEach((v, i) => {
      const x = (i / 255) * W;
      const y = H - (v / max) * (H - 8);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.lineTo(W, H); ctx.lineTo(0, H); ctx.closePath();
    ctx.fillStyle = "rgba(53,242,255,0.22)";
    ctx.fill();
    ctx.strokeStyle = "#35f2ff";
    ctx.lineWidth = 2;
    ctx.stroke();
  } catch (err) {
    console.warn("Histogram draw skipped:", err);
  }
}

refreshOutputs();
