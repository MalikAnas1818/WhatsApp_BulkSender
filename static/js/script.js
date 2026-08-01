let state = {
  numbers: [],
  validNumbers: [],
  invalidNumbers: [],
  message: "",
  attachmentPath: null,
  attachmentName: null,
  jobId: null,
};

// ---------- STEP NAV ----------
function goToStep(n){
  document.querySelectorAll(".panel").forEach(p => p.classList.add("hidden"));
  document.getElementById(`step-${n}`).classList.remove("hidden");

  document.querySelectorAll(".signal-step").forEach(s => {
    const step = parseInt(s.dataset.step);
    s.classList.toggle("active", step === n);
    s.classList.toggle("done", step < n);
  });
}

// ---------- TABS (paste vs upload) ----------
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`.tab-panel[data-tab-panel="${tab.dataset.tab}"]`).classList.add("active");
  });
});

// ---------- FILE UPLOAD (numbers) ----------
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
let uploadedNumbers = [];

fileInput.addEventListener("change", handleFile);
dropzone.addEventListener("dragover", e => { e.preventDefault(); dropzone.classList.add("drag"); });
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag"));
dropzone.addEventListener("drop", e => {
  e.preventDefault();
  dropzone.classList.remove("drag");
  if (e.dataTransfer.files.length){
    fileInput.files = e.dataTransfer.files;
    handleFile();
  }
});

async function handleFile(){
  const file = fileInput.files[0];
  if (!file) return;
  document.getElementById("dropzoneText").textContent = `Reading ${file.name}...`;

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/upload", { method: "POST", body: formData });
  const data = await res.json();

  if (data.error){
    document.getElementById("dropzoneText").textContent = `Error: ${data.error}`;
    return;
  }

  uploadedNumbers = data.numbers;
  document.getElementById("dropzoneText").textContent = `${file.name} — ${data.count} numbers found`;
}

// ---------- ATTACHMENT UPLOAD (for message) ----------
document.getElementById("attachInput").addEventListener("change", async () => {
  const file = document.getElementById("attachInput").files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch("/api/upload-attachment", { method: "POST", body: formData });
  const data = await res.json();

  if (data.error) return;

  state.attachmentPath = data.path;
  state.attachmentName = data.name;
  document.getElementById("attachName").textContent = data.name;
});

// ---------- STEP 1 -> STEP 2 : gather + validate numbers ----------
document.getElementById("toStep2").addEventListener("click", async () => {
  const activeTab = document.querySelector(".tab.active").dataset.tab;
  let rawNumbers = [];

  if (activeTab === "paste"){
    const text = document.getElementById("pasteArea").value;
    const res = await fetch("/api/parse-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    const data = await res.json();
    rawNumbers = data.numbers;
  } else {
    rawNumbers = uploadedNumbers;
  }

  if (!rawNumbers.length){
    alert("No numbers found yet — paste some numbers or upload a file first.");
    return;
  }

  document.getElementById("foundStrip").style.display = "block";
  document.getElementById("foundCount").textContent = rawNumbers.length;

  const defaultRegion = document.getElementById("defaultRegion").value.trim().toUpperCase() || null;

  const valRes = await fetch("/api/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ numbers: rawNumbers, default_region: defaultRegion })
  });
  const valData = await valRes.json();

  state.validNumbers = valData.valid;
  state.invalidNumbers = valData.invalid;

  if (!state.validNumbers.length){
    alert("None of these numbers validated. If they don't start with +countrycode, try setting a default country code.");
    return;
  }

  document.getElementById("validCountLabel").textContent = state.validNumbers.length;
  goToStep(2);
});

document.getElementById("backTo1").addEventListener("click", () => goToStep(1));

// ---------- STEP 2 -> STEP 3 : preview ----------
document.getElementById("toStep3").addEventListener("click", () => {
  const message = document.getElementById("messageArea").value.trim();
  if (!message){
    alert("Write a message first.");
    return;
  }
  state.message = message;

  document.getElementById("previewValidCount").textContent = state.validNumbers.length;
  document.getElementById("previewInvalidCount").textContent = state.invalidNumbers.length;
  document.getElementById("previewMessage").textContent = state.message;
  document.getElementById("sendCount").textContent = state.validNumbers.length;

  const attachEl = document.getElementById("previewAttach");
  if (state.attachmentName){
    attachEl.style.display = "block";
    attachEl.textContent = `📎 ${state.attachmentName}`;
  } else {
    attachEl.style.display = "none";
  }

  const chipList = document.getElementById("numberChipList");
  chipList.innerHTML = "";
  state.validNumbers.slice(0, 12).forEach(n => {
    const chip = document.createElement("span");
    chip.className = "number-chip";
    chip.textContent = n;
    chipList.appendChild(chip);
  });
  if (state.validNumbers.length > 12){
    const chip = document.createElement("span");
    chip.className = "number-chip";
    chip.textContent = `+${state.validNumbers.length - 12} more`;
    chipList.appendChild(chip);
  }

  goToStep(3);
});

document.getElementById("backTo2").addEventListener("click", () => goToStep(2));

// ---------- STEP 3 -> STEP 4 : send ----------
document.getElementById("toStep4").addEventListener("click", async () => {
  goToStep(4);
  document.getElementById("totalCount").textContent = state.validNumbers.length;
  document.getElementById("logFeed").innerHTML = "";
  document.getElementById("downloadLog").style.display = "none";
  document.getElementById("sendingTitle").textContent = "Opening Chrome...";
  document.getElementById("sendingSub").textContent = "A Chrome window will open. Scan the QR code with WhatsApp on your phone if this is the first time.";

  const res = await fetch("/api/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      numbers: state.validNumbers,
      message: state.message,
      attachment_path: state.attachmentPath,
    })
  });
  const data = await res.json();

  if (data.error){
    document.getElementById("sendingTitle").textContent = "Couldn't start";
    document.getElementById("sendingSub").textContent = data.error;
    return;
  }

  state.jobId = data.job_id;
  pollProgress();
});

document.getElementById("cancelSend").addEventListener("click", async () => {
  if (!state.jobId) return;
  await fetch(`/api/cancel/${state.jobId}`, { method: "POST" });
});

document.getElementById("downloadLog").addEventListener("click", () => {
  if (!state.jobId) return;
  window.location.href = `/api/download-log/${state.jobId}`;
});

const STATUS_LABELS = {
  starting: ["Getting ready...", "Setting things up before we open Chrome."],
  launching_chrome: ["Opening Chrome...", "A Chrome window is launching — this only takes a moment."],
  waiting_for_qr: ["Waiting for WhatsApp login", "Scan the QR code shown in the Chrome window using WhatsApp on your phone."],
  sending: ["Sending messages", "Keep the Chrome window open in the background while this runs."],
  completed: ["All done", "Every number has been processed. You can download the log below."],
  cancelled: ["Cancelled", "Sending was stopped early. Numbers already sent stay sent."],
  error: ["Something went wrong", "Check the details below."],
};

function renderLogLine(entry){
  const ok = entry.status === "Success";
  return `<div class="log-line"><span class="t">${entry.time}</span><span class="${ok ? "ok" : "bad"}">${ok ? "✓" : "✕"}</span><span>${entry.number}</span><span class="t">${entry.detail}</span></div>`;
}

async function pollProgress(){
  if (!state.jobId) return;

  const res = await fetch(`/api/progress/${state.jobId}`);
  const data = await res.json();

  const labels = STATUS_LABELS[data.status] || [data.status, ""];
  document.getElementById("sendingTitle").textContent = labels[0];
  document.getElementById("sendingSub").textContent = data.error || labels[1];

  document.getElementById("sentCount").textContent = data.sent;
  document.getElementById("failCount").textContent = data.failed;
  document.getElementById("totalCount").textContent = data.total;

  const donePct = data.total ? Math.round(((data.sent + data.failed) / data.total) * 100) : 0;
  document.getElementById("progressBar").style.width = `${donePct}%`;

  const feed = document.getElementById("logFeed");
  feed.innerHTML = data.log.map(renderLogLine).join("");
  feed.scrollTop = feed.scrollHeight;

  const finished = ["completed", "cancelled", "error"].includes(data.status);
  if (finished){
    if (data.status === "completed" || data.status === "cancelled"){
      document.getElementById("downloadLog").style.display = "inline-block";
    }
    document.getElementById("cancelSend").style.display = "none";
    return;
  }

  setTimeout(pollProgress, 1500);
}
