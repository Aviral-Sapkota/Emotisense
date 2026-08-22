'use strict';

//  Emotion display config (7 emotions matching your CNN) 
const EMOTIONS = {
  angry:    { emoji: '😠', color: '#f87171' },
  disgust:  { emoji: '🤢', color: '#34d399' },
  fear:     { emoji: '😨', color: '#a78bfa' },
  happy:    { emoji: '😄', color: '#4ade80' },
  sad:      { emoji: '😢', color: '#60a5fa' },
  surprise: { emoji: '😮', color: '#fbbf24' },
  neutral:  { emoji: '😐', color: '#94a3b8' },
};

//  State 
let mediaStream   = null;
let autoTimer     = null;
let autoInterval  = 3;       // seconds
let sessionTotal  = 0;
let sessionCounts = {};
let totalFaces    = 0;

//  Init 
window.addEventListener('DOMContentLoaded', () => {
  if (!localStorage.getItem('token')) { window.location.href = '/'; return; }

  document.getElementById('user-greeting').textContent =
    'Hello, ' + (localStorage.getItem('first_name') || '');

  loadDbStats();
  checkExistingPushSubscription();
});

async function loadDbStats() {
  try {
    const s = await apiFetch('/api/scans/stats');
    document.getElementById('stat-db').textContent = s.total_scans || 0;
  } catch {}
}

//  Camera 

async function startCamera() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false,
    });
    const video = document.getElementById('webcam');
    video.srcObject = mediaStream;
    video.style.display = 'block';

    document.getElementById('cam-placeholder').style.display = 'none';
    document.getElementById('live-overlay').style.display    = 'block';
    document.getElementById('face-indicator').style.display  = 'block';
    document.getElementById('btn-start').disabled            = true;
    document.getElementById('btn-analyze').disabled          = false;
    document.getElementById('btn-stop').disabled             = false;
  } catch (err) {
    alert('Camera access denied.\n\nPlease allow camera permissions in your browser.\n\nError: ' + err.message);
  }
}

function stopCamera() {
  if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); mediaStream = null; }

  // Stop auto-analyze if running
  if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
  document.getElementById('auto-analyze').checked = false;
  document.getElementById('auto-interval').style.display = 'none';

  const video = document.getElementById('webcam');
  video.srcObject = null;
  video.style.display = 'none';

  document.getElementById('cam-placeholder').style.display = 'flex';
  document.getElementById('live-overlay').style.display    = 'none';
  document.getElementById('face-indicator').style.display  = 'none';
  document.getElementById('btn-start').disabled            = false;
  document.getElementById('btn-analyze').disabled          = true;
  document.getElementById('btn-stop').disabled             = true;
}

function captureFrame() {
  const video  = document.getElementById('webcam');
  const canvas = document.getElementById('snap-canvas');
  canvas.width  = video.videoWidth  || 640;
  canvas.height = video.videoHeight || 480;
  canvas.getContext('2d').drawImage(video, 0, 0);
  // Strip "data:image/jpeg;base64," prefix — backend expects raw base64
  return canvas.toDataURL('image/jpeg', 0.85).split(',')[1];
}

//  Auto-analyze 

function toggleAuto(checkbox) {
  const slider = document.getElementById('auto-interval');
  if (checkbox.checked) {
    slider.style.display = 'block';
    autoTimer = setInterval(analyzeEmotion, autoInterval * 1000);
  } else {
    slider.style.display = 'none';
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
  }
}

function updateInterval(slider) {
  autoInterval = parseInt(slider.value);
  document.getElementById('auto-interval-label').textContent = autoInterval + 's';
  if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = setInterval(analyzeEmotion, autoInterval * 1000);
  }
}

//  Analysis 

let analyzing = false;  // prevent concurrent requests during auto-analyze

async function analyzeEmotion() {
  if (analyzing) return;
  analyzing = true;

  // Switch to analyzing state
  showResultState('analyzing');
  document.getElementById('btn-analyze').disabled = true;

  try {
    const image  = captureFrame();
    const result = await apiFetch('/api/analyze', {
      method: 'POST',
      body:   JSON.stringify({ image }),
    });

    if (result.faces_detected === 0) {
      // No face found — show message but still update history
      showResultState('no-face');
      document.getElementById('no-face-msg').textContent =
        result.message || 'No face detected. Please face the camera.';
    } else {
      showResultState('result');
      renderResult(result);
    }

    // Always add to history and update stats
    addToHistory(result);
    updateStats(result);

  } catch (err) {
    showResultState('idle');
    document.getElementById('state-idle').querySelector('p').textContent =
      '⚠ ' + (err.detail || err.message || 'Analysis failed.');
  } finally {
    analyzing = false;
    document.getElementById('btn-analyze').disabled = false;
  }
}

//  UI state switcher 

function showResultState(state) {
  ['idle', 'analyzing', 'no-face', 'result'].forEach(s => {
    const el = document.getElementById('state-' + s);
    if (el) el.style.display = s === state ? (s === 'result' ? 'block' : 'flex') : 'none';
  });
}

//  Result rendering 

function renderResult(result) {
  const info = EMOTIONS[result.primary] || { emoji: '🎭', color: '#94a3b8' };

  // Hero
  document.getElementById('res-emoji').textContent = info.emoji;
  document.getElementById('res-name').textContent  =
    result.primary.charAt(0).toUpperCase() + result.primary.slice(1);

  // Confidence bar
  const conf = result.confidence.toFixed(1);
  document.getElementById('conf-bar').style.width = conf + '%';
  document.getElementById('res-conf').textContent  = conf + '%';

  // Face count indicator
  document.getElementById('face-count-label').textContent =
    result.faces_detected + (result.faces_detected === 1 ? ' face' : ' faces');

  // Emotion bars — sorted highest to lowest
  const bars = document.getElementById('emotion-bars');
  bars.innerHTML = '';

  const sorted = Object.entries(result.scores).sort(([,a],[,b]) => b - a);
  const isTop  = true;

  sorted.forEach(([emotion, pct], idx) => {
    const meta = EMOTIONS[emotion] || { emoji: '🎭', color: '#94a3b8' };
    const row  = document.createElement('div');
    row.className = 'bar-row';
    row.innerHTML = `
      <div class="bar-label">${meta.emoji} ${emotion}</div>
      <div class="bar-track">
        <div class="bar-fill" style="width:0%;background:${meta.color};"></div>
      </div>
      <div class="bar-pct ${idx === 0 ? 'top' : ''}">${pct.toFixed(1)}%</div>
    `;
    bars.appendChild(row);

    // Animate bar width
    requestAnimationFrame(() => requestAnimationFrame(() => {
      row.querySelector('.bar-fill').style.width = pct + '%';
    }));
  });
}

//  History 

function addToHistory(result) {
  const list = document.getElementById('history-list');

  // Remove placeholder if present
  const ph = list.querySelector('.placeholder-state');
  if (ph) ph.remove();

  const time = new Date().toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' });
  const info = EMOTIONS[result.primary] || { emoji: '🎭' };

  const item = document.createElement('div');
  item.className = 'history-item';
  item.innerHTML = `
    <span class="h-emoji">${result.faces_detected === 0 ? '🔍' : info.emoji}</span>
    <span class="h-name">${result.faces_detected === 0 ? 'No face' : result.primary.charAt(0).toUpperCase()+result.primary.slice(1)}</span>
    <span class="h-pct">${result.faces_detected === 0 ? '—' : result.confidence.toFixed(1)+'%'}</span>
    <span class="h-time">${time}</span>
  `;
  list.insertBefore(item, list.firstChild);

  // Keep last 15 entries
  while (list.children.length > 15) list.removeChild(list.lastChild);
}

function clearHistory() {
  document.getElementById('history-list').innerHTML = `
    <div class="placeholder-state" style="padding:1rem 0;">
      <div class="ph-icon" style="font-size:22px;">📋</div>
      <p style="font-size:12px;">No scans yet this session</p>
    </div>
  `;
}

//  Session stats 

function updateStats(result) {
  sessionTotal++;
  document.getElementById('stat-session').textContent = sessionTotal;

  if (result.faces_detected > 0) {
    totalFaces += result.faces_detected;
    document.getElementById('stat-faces').textContent = totalFaces;

    sessionCounts[result.primary] = (sessionCounts[result.primary] || 0) + 1;
    const top = Object.entries(sessionCounts).sort(([,a],[,b]) => b-a)[0];
    const info = EMOTIONS[top[0]] || { emoji:'' };
    document.getElementById('stat-top').textContent = info.emoji + ' ' + top[0];
  }

  // Refresh DB total every 5 scans
  if (sessionTotal % 5 === 0) loadDbStats();
}
