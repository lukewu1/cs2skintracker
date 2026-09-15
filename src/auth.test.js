import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  API_URL,
  SessionExpiredError,
  authFetch,
  clearToken,
  getToken,
  isLoggedIn,
  setToken,
} from './auth'

// Node's own built-in localStorage global behaves inconsistently across
// versions/environments, so auth.js's ambient `localStorage` is stubbed
// with a plain in-memory fake rather than relying on jsdom or Node's own.
function fakeLocalStorage() {
  const store = new Map()
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
    removeItem: (key) => store.delete(key),
  }
}

beforeEach(() => {
  vi.stubGlobal('localStorage', fakeLocalStorage())
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('token storage', () => {
  it('is empty until a token is set', () => {
    expect(getToken()).toBeNull()
    expect(isLoggedIn()).toBe(false)
  })

  it('round-trips through setToken/getToken', () => {
    setToken('abc123')
    expect(getToken()).toBe('abc123')
    expect(isLoggedIn()).toBe(true)
  })

  it('clearToken removes it', () => {
    setToken('abc123')
    clearToken()
    expect(getToken()).toBeNull()
    expect(isLoggedIn()).toBe(false)
  })
})

describe('authFetch', () => {
  function mockFetch(response) {
    const fn = vi.fn().mockResolvedValue(response)
    vi.stubGlobal('fetch', fn)
    return fn
  }

  it('omits Authorization when there is no token', async () => {
    const fetchMock = mockFetch({ status: 200, ok: true })
    await authFetch('/api/skins')

    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe(`${API_URL}/api/skins`)
    expect(options.headers.Authorization).toBeUndefined()
  })

  it('adds a bearer Authorization header when a token is set', async () => {
    setToken('my-token')
    const fetchMock = mockFetch({ status: 200, ok: true })
    await authFetch('/api/skins')

    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers.Authorization).toBe('Bearer my-token')
  })

  it('preserves caller-supplied headers alongside Authorization', async () => {
    setToken('my-token')
    const fetchMock = mockFetch({ status: 200, ok: true })
    await authFetch('/api/skins', { headers: { 'X-Test': '1' } })

    const [, options] = fetchMock.mock.calls[0]
    expect(options.headers).toEqual({ 'X-Test': '1', Authorization: 'Bearer my-token' })
  })

  it('clears the token and throws SessionExpiredError on a 401', async () => {
    setToken('my-token')
    mockFetch({ status: 401, ok: false })

    await expect(authFetch('/api/skins')).rejects.toThrow(SessionExpiredError)
    expect(getToken()).toBeNull()
  })

  it('returns the raw response as-is on success', async () => {
    const response = { status: 200, ok: true, json: async () => ({ hello: 'world' }) }
    mockFetch(response)

    const result = await authFetch('/api/skins')
    expect(result).toBe(response)
  })

  it('returns the raw response on a non-401 error status too', async () => {
    // authFetch only special-cases 401; other error statuses are left for
    // the caller to handle, not thrown here.
    const response = { status: 500, ok: false }
    mockFetch(response)

    const result = await authFetch('/api/skins')
    expect(result).toBe(response)
  })
})
