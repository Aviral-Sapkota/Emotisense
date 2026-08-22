const API_BASE = "https://emotisense-2-zl5f.onrender.com";
async function apiFetch(url, opts = {}) {
  const token = localStorage.getItem('token');
  const res = await fetch(API_BASE + url, {
    ...opts,
    headers: {
      'Content-Type':  'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
      ...(opts.headers || {}),
    },
  });

  // Token expired → kick to login
  if (res.status === 401) {
    localStorage.clear();
    window.location.href = '/';
    return;
  }

  const data = await res.json();
  if (!res.ok) {
    const err  = new Error(data.detail || 'Request failed');
    err.detail = data.detail;
    err.status = res.status;
    throw err;
  }
  return data;
}

function logout() {
  localStorage.clear();
  window.location.href = '/';
}
