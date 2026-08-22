function urlBase64ToUint8Array(b64) {
  const pad  = '='.repeat((4 - b64.length % 4) % 4);
  const base = (b64 + pad).replace(/-/g, '+').replace(/_/g, '/');
  return new Uint8Array([...atob(base)].map(c => c.charCodeAt(0)));
}
function ab2b64(buf) {
  return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}

async function enablePush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return updatePushUI('unsupported');
  }
  const perm = await Notification.requestPermission();
  if (perm !== 'granted') return updatePushUI('denied');

  try {
    const { public_key } = await apiFetch('/api/push/vapid-public-key');
    const reg = await navigator.serviceWorker.register('/static/js/sw.js');
    await navigator.serviceWorker.ready;

    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
      });
    }

    await apiFetch('/api/push/subscribe', {
      method: 'POST',
      body: JSON.stringify({
        endpoint: sub.endpoint,
        p256dh:   ab2b64(sub.getKey('p256dh')),
        auth:     ab2b64(sub.getKey('auth')),
      }),
    });
    updatePushUI('enabled');
  } catch (e) {
    console.error('Push setup failed:', e);
    updatePushUI('error');
  }
}

function updatePushUI(state) {
  const btn   = document.getElementById('btn-enable-push');
  const label = document.getElementById('push-state-label');
  const map   = {
    enabled:     ['✓ Notifications on',    '✅ This device is subscribed'],
    denied:      ['Permission denied',      '⚠ Allow notifications in browser settings'],
    unsupported: ['Not supported',          '⚠ Your browser does not support Web Push'],
    error:       ['Setup failed',           '⚠ Check VAPID keys in .env'],
  };
  const [b, l] = map[state] || ['Enable notifications', ''];
  if (btn)   btn.textContent   = b;
  if (label) label.textContent = l;
}

async function loadRules() {
  try {
    const rules = await apiFetch('/api/push/rules');
    renderRules(rules);
  } catch { /* push not configured */ }
}

const EMOJI7 = { angry:'😠',disgust:'🤢',fear:'😨',happy:'😄',sad:'😢',surprise:'😮',neutral:'😐' };

function renderRules(rules) {
  const el = document.getElementById('rules-list');
  if (!el) return;
  if (!rules.length) {
    el.innerHTML = '<p style="font-size:12px;color:var(--muted);">No rules yet — add one above.</p>';
    return;
  }
  el.innerHTML = rules.map(r => `
    <div class="rule-item">
      <span class="rule-item-lbl">${EMOJI7[r.emotion]||''} ${r.emotion} ≥ ${r.threshold}%</span>
      <button class="rule-del" onclick="deleteRule(${r.id})" title="Delete">✕</button>
    </div>
  `).join('');
}

async function addRule() {
  const emotion   = document.getElementById('rule-emotion').value;
  const threshold = parseFloat(document.getElementById('rule-threshold').value);
  if (!emotion || isNaN(threshold)) return;
  try {
    await apiFetch('/api/push/rules', { method:'POST', body: JSON.stringify({emotion, threshold, enabled:true}) });
    await loadRules();
  } catch (e) { alert(e.detail || 'Could not add rule.'); }
}

async function deleteRule(id) {
  try {
    await apiFetch(`/api/push/rules/${id}`, { method:'DELETE' });
    await loadRules();
  } catch (e) { alert(e.detail || 'Could not delete rule.'); }
}

function toggleNotifPanel() {
  const p = document.getElementById('notif-panel');
  const open = p.style.display !== 'none';
  p.style.display = open ? 'none' : 'block';
  if (!open) loadRules();
}

async function checkExistingPushSubscription() {
  if (!('serviceWorker' in navigator)) return;
  try {
    const reg = await navigator.serviceWorker.register('/static/js/sw.js', {
  scope: '/'
  });
    if (!reg) return;
    const sub = await reg.pushManager.getSubscription();
    if (sub) updatePushUI('enabled');
  } catch (err) {
    console.error('Push subscription check failed:', err); 
  }
}
