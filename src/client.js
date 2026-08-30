const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';
const TOKEN_KEY = 'auth_token';

let onUnauthorized = null;

export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// FastAPI errors are {"detail": ...}. `detail` is a string for HTTPException
// but an array of objects for 422 validation errors, so handle both.
async function extractError(response) {
  try {
    const data = await response.json();
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((e) => e.msg).join(', ');
    }
  } catch {
    // Body wasn't JSON — fall through.
  }
  return `Request failed (${response.status})`;
}

export async function register(username, password) {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) throw new Error(await extractError(response));
  return response.json();
}

export async function login(username, password) {
  // OAuth2PasswordRequestForm requires form encoding, not JSON.
  // Do NOT set Content-Type — the browser sets it with the correct boundary.
  const body = new URLSearchParams({ username, password });

  const response = await fetch(`${API_BASE_URL}/api/auth/token`, {
    method: 'POST',
    body,
  });

  if (!response.ok) throw new Error(await extractError(response));

  const data = await response.json();
  if (!data.access_token) throw new Error('No token in response');

  setToken(data.access_token);
  return data;
}

export async function fetchWithAuth(path, options = {}) {
  const token = getToken();
  const headers = { ...options.headers };

  if (token) headers['Authorization'] = `Bearer ${token}`;
  // Only send Content-Type when there's actually a body to describe.
  if (options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401 || response.status === 403) {
    clearToken();
    onUnauthorized?.();
    throw new Error('Session expired. Please log in again.');
  }

  if (!response.ok) throw new Error(await extractError(response));

  if (response.status === 204) return null;
  return response.json();
}

export function getMe() {
  return fetchWithAuth('/api/auth/me');
}

export function getListings(params) {
  const query = new URLSearchParams(params).toString();
  return fetchWithAuth(`/api/listings?${query}`);
}