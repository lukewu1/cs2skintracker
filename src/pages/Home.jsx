import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { clearToken } from '../auth'
import './Home.css'

const STORAGE_KEY = 'watchlist'
const DEFAULT_WATCHLIST = [
  'AK-47 | Redline (Field-Tested)',
  'AWP | Asiimov (Field-Tested)',
]

function loadWatchlist() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : null
    return Array.isArray(parsed) ? parsed : DEFAULT_WATCHLIST
  } catch {
    return DEFAULT_WATCHLIST
  }
}

function Home() {
  const navigate = useNavigate()

  const [inputValue, setInputValue] = useState('')
  // lazy initializer so localStorage is read once, not on every render
  const [watchlist, setWatchlist] = useState(loadWatchlist)
  const [message, setMessage] = useState('')

  // Persisting here means the list survives a refresh and the login
  // redirect, neither of which router state does.
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist))
    } catch {
      // storage full or blocked: the list still works for this session 
    }
  }, [watchlist])

  const handleAddItem = (e) => {
    e.preventDefault()
    setMessage('')

    const trimmed = inputValue.trim()
    if (!trimmed) return

    if (watchlist.includes(trimmed)) {
      setMessage('That skin is already on your watchlist.')
      return
    }

    setWatchlist([...watchlist, trimmed])
    setInputValue('')
  }

  const handleRemoveItem = (skin) => {
    setMessage('')
    setWatchlist(watchlist.filter((s) => s !== skin))
  }

  const handleScan = () => {
    navigate('/deals', { state: { watchlist } })
  }

  const handleSignOut = () => {
    clearToken()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <img src="/cs2skintracker.png" alt="" width="32" height="32" />
        <span className="app-wordmark">CS2 Skin Tracker</span>
        <div className="app-header-spacer" />
        <button type="button" className="app-link" onClick={handleSignOut}>
          Sign out
        </button>
      </header>

      <h1 className="app-title">Your watchlist</h1>
      <p className="app-subtitle">
        Add the skins you want to track. Scanning checks every one against live
        CSFloat listings and sorts them by whichever measure you pick.
      </p>

      {message && <div className="app-note" role="status">{message}</div>}

      <form className="app-add" onSubmit={handleAddItem}>
        <input
          type="text"
          aria-label="Skin name"
          placeholder="e.g. Desert Eagle | Printstream (Field-Tested)"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
        />
        <button
          type="submit"
          className="app-button-secondary"
          disabled={!inputValue.trim()}
        >
          Add
        </button>
      </form>

      {watchlist.length === 0 ? (
        <div className="app-empty">
          Nothing tracked yet. Add a skin above to get started.
        </div>
      ) : (
        <ul className="app-list">
          {watchlist.map((skin) => (
            <li key={skin}>
              <span className="app-item-name">{skin}</span>
              <button
                type="button"
                className="app-remove"
                aria-label={`Remove ${skin}`}
                onClick={() => handleRemoveItem(skin)}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        type="button"
        className="app-button"
        onClick={handleScan}
        disabled={watchlist.length === 0}
      >
        Scan {watchlist.length} {watchlist.length === 1 ? 'skin' : 'skins'}
      </button>

      {watchlist.length === 0 && (
        <p className="app-hint">Add at least one skin to scan.</p>
      )}
    </div>
  )
}

export default Home