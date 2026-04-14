/* global fetch, localStorage */
const API_BASE = 'http://localhost:8000/api/v1';

function createApiFetch(tokenStore) {
  const { getToken, getRefreshToken, onLogout, onTokenRefreshed } = tokenStore;

  async function doRefresh() {
    const rt = getRefreshToken();
    if (!rt) { onLogout(); return false; }
    try {
      const r = await fetch(API_BASE + '/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt })
      });
      if (r.ok) {
        const d = await r.json();
        onTokenRefreshed(d.access_token, d.refresh_token);
        return true;
      }
    } catch (_) { /* network error */ }
    onLogout();
    return false;
  }

  return async function apiFetch(endpoint, options) {
    options = options || {};
    const token = getToken();
    if (!token) throw new Error('Not authenticated');

    const headers = Object.assign({ Authorization: 'Bearer ' + token }, options.headers || {});
    let body = options.body;
    if (body && typeof body === 'object' && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(body);
    }

    const reqOpts = Object.assign({}, options, { headers: headers, body: body });
    let resp = await fetch(API_BASE + endpoint, reqOpts);

    if (resp.status === 401) {
      const ok = await doRefresh();
      if (ok) {
        reqOpts.headers.Authorization = 'Bearer ' + getToken();
        resp = await fetch(API_BASE + endpoint, reqOpts);
      } else {
        throw new Error('Session expired');
      }
    }
    return resp;
  };
}