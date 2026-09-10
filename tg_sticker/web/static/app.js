let currentFile = null;

// Tab navigation
function switchTab(tab) {
  document.getElementById('singleView').classList.toggle('active', tab === 'single');
  document.getElementById('batchView').classList.toggle('active', tab === 'batch');
  document.getElementById('tabSingleBtn').classList.toggle('active', tab === 'single');
  document.getElementById('tabBatchBtn').classList.toggle('active', tab === 'batch');

  if (tab === 'batch') {
    refreshFolders();
  }
}

// Drag & Drop Setup
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('click', (e) => {
  if (e.target.id !== 'clearFileBtn') {
    fileInput.click();
  }
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length > 0) {
    handleFileSelected(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) {
    handleFileSelected(e.target.files[0]);
  }
});

document.getElementById('clearFileBtn').addEventListener('click', (e) => {
  e.stopPropagation();
  currentFile = null;
  fileInput.value = '';
  document.getElementById('dropzonePrompt').classList.remove('hidden');
  document.getElementById('fileInfo').classList.add('hidden');
  document.getElementById('inputPreviewBox').classList.add('hidden');
  document.getElementById('convertBtn').disabled = true;
});

function handleFileSelected(file) {
  currentFile = file;
  document.getElementById('fileName').textContent = file.name;
  document.getElementById('fileMeta').textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;

  document.getElementById('dropzonePrompt').classList.add('hidden');
  document.getElementById('fileInfo').classList.remove('hidden');
  document.getElementById('convertBtn').disabled = false;

  // Load preview
  const video = document.getElementById('sourceVideo');
  video.src = URL.createObjectURL(file);
  document.getElementById('inputPreviewBox').classList.remove('hidden');

  video.onloadedmetadata = () => {
    const dur = Math.min(video.duration, 3.0);
    document.getElementById('duration').value = dur.toFixed(1);
  };
}

function setStartFromCurrent() {
  const video = document.getElementById('sourceVideo');
  if (video) {
    document.getElementById('startTime').value = video.currentTime.toFixed(1);
  }
}

function toggleMode() {
  const mode = document.querySelector('input[name="mode"]:checked').value;
  const emojiRow = document.getElementById('emojiFitRow');
  if (mode === 'emoji') {
    emojiRow.style.display = 'flex';
  } else {
    emojiRow.style.display = 'none';
  }
}

// Single Conversion
async function runConversion() {
  if (!currentFile) return;

  const mode = document.querySelector('input[name="mode"]:checked').value;
  const loopMode = document.querySelector('input[name="loopMode"]:checked').value;
  const startTime = document.getElementById('startTime').value;
  const duration = document.getElementById('duration').value;
  const speedToFit = document.getElementById('speedToFit').checked;
  const fitMode = document.getElementById('fitMode').value;
  const removeBg = document.getElementById('removeBg').value;

  const formData = new FormData();
  formData.append('video', currentFile);
  formData.append('filename', currentFile.name);
  formData.append('mode', mode);
  formData.append('loop_mode', loopMode);
  formData.append('start_time', startTime);
  formData.append('duration', duration);
  formData.append('speed_to_fit', speedToFit);
  formData.append('fit_mode', fitMode);
  formData.append('remove_bg', removeBg);

  // UI state
  document.getElementById('emptyState').classList.add('hidden');
  document.getElementById('resultBox').classList.add('hidden');
  document.getElementById('loadingIndicator').classList.remove('hidden');
  document.getElementById('convertBtn').disabled = true;

  try {
    const res = await fetch('/api/convert', {
      method: 'POST',
      body: formData,
    });

    const data = await res.json();
    if (!res.ok || data.error) {
      alert(`Error during conversion: ${data.error || 'Unknown error'}`);
      return;
    }

    // Display output
    const outVideo = document.getElementById('outputVideo');
    outVideo.src = data.download_url + '?t=' + Date.now();
    outVideo.play();

    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.href = data.download_url;
    downloadBtn.download = data.filename;

    renderChecklist(data, mode);

    document.getElementById('resultBox').classList.remove('hidden');
  } catch (err) {
    alert(`Failed to communicate with converter: ${err.message}`);
  } finally {
    document.getElementById('loadingIndicator').classList.add('hidden');
    document.getElementById('convertBtn').disabled = false;
  }
}

function renderChecklist(data, mode) {
  const list = document.getElementById('checklist');
  list.innerHTML = '';

  const info = data.info || {};
  const isSticker = mode === 'sticker';

  const items = [
    {
      name: 'Format (.WEBM)',
      value: 'VP9 WebM',
      pass: info.codec === 'vp9',
    },
    {
      name: isSticker ? 'Dimensions (512px max side)' : 'Dimensions (100x100)',
      value: `${info.width}x${info.height}`,
      pass: isSticker
        ? Math.max(info.width, info.height) === 512 && Math.min(info.width, info.height) <= 512
        : info.width === 100 && info.height === 100,
    },
    {
      name: 'Duration (&le; 3.0s)',
      value: `${info.duration ? info.duration.toFixed(2) : 0}s`,
      pass: (info.duration || 0) <= 3.05,
    },
    {
      name: 'File Size (&le; 256 KB)',
      value: `${info.size_kb ? info.size_kb.toFixed(1) : 0} KB`,
      pass: (info.size_bytes || 0) <= 256 * 1024,
    },
    {
      name: 'Audio Stream',
      value: info.has_audio ? 'Detected (Invalid)' : 'None (Compliant)',
      pass: !info.has_audio,
    },
    {
      name: 'Alpha Transparency',
      value: info.has_alpha ? 'Supported (YUVA420P)' : 'None',
      pass: true,
    }
  ];

  items.forEach(it => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span>${it.name}</span>
      <span class="${it.pass ? 'check-pass' : 'check-fail'}">
        ${it.pass ? '✓' : '✗'} ${it.value}
      </span>
    `;
    list.appendChild(li);
  });
}

// Batch Folder Manager
async function refreshFolders() {
  try {
    const res = await fetch('/api/folders');
    const data = await res.json();

    const inList = document.getElementById('inputFileList');
    const outList = document.getElementById('outputFileList');

    document.getElementById('inputCount').textContent = data.input_files.length;
    document.getElementById('outputCount').textContent = data.output_files.length;

    if (data.input_files.length === 0) {
      inList.innerHTML = '<p class="empty-hint">No videos found in input_videos/</p>';
    } else {
      inList.innerHTML = data.input_files.map(f => `<div class="file-item">🎬 ${f}</div>`).join('');
    }

    if (data.output_files.length === 0) {
      outList.innerHTML = '<p class="empty-hint">No stickers yet in output_stickers/</p>';
    } else {
      outList.innerHTML = data.output_files.map(f => `<div class="file-item">⚡ ${f}</div>`).join('');
    }
  } catch (err) {
    console.error('Failed to refresh folders:', err);
  }
}

async function runBatchConversion() {
  const mode = document.getElementById('batchMode').value;
  const speedToFit = document.getElementById('batchSpeed').checked;
  const pingpong = document.getElementById('batchPingpong').checked;
  const overwrite = document.getElementById('batchOverwrite').checked;

  const btn = document.getElementById('runBatchBtn');
  const progBox = document.getElementById('batchProgressBox');
  const statusText = document.getElementById('batchStatusText');

  btn.disabled = true;
  progBox.classList.remove('hidden');
  statusText.textContent = 'Processing folder videos with FFmpeg VP9...';

  try {
    const res = await fetch('/api/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        mode,
        speed_to_fit: speedToFit,
        loop_mode: pingpong ? 'pingpong' : 'normal',
        overwrite,
      }),
    });

    const data = await res.json();
    if (data.success) {
      statusText.textContent = `Completed! ${data.succeeded} converted, ${data.skipped} skipped, ${data.failed} failed.`;
      refreshFolders();
    } else {
      statusText.textContent = `Batch error: ${data.error}`;
    }
  } catch (err) {
    statusText.textContent = `Network error: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
}
