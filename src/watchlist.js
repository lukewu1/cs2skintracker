export const STORAGE_KEY = 'watchlist'

export const DEFAULT_WATCHLIST = [
  'AK-47 | Redline (Field-Tested)',
  'AWP | Asiimov (Field-Tested)',
]

export function loadWatchlist() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : null
    return Array.isArray(parsed) ? parsed : DEFAULT_WATCHLIST
  } catch {
    return DEFAULT_WATCHLIST
  }
}
