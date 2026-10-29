import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authFetch, clearToken, SessionExpiredError } from '../auth'
import { STORAGE_KEY, loadWatchlist } from '../watchlist'
import { WEARS, buildCatalog, resolveSkin, variantsOf } from '../skins'
import './app.css'

function Home() {
  const navigate = useNavigate()

  const [weapon, setWeapon] = useState('')
  const [finish, setFinish] = useState('')
  const [wear, setWear] = useState('Field-Tested')
  const [statTrak, setStatTrak] = useState(false)
  // lazy initializer so localStorage is read once, not on every render
  const [watchlist, setWatchlist] = useState(loadWatchlist)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  // null while loading; the names the scraper has data for
  const [catalog, setCatalog] = useState(null)
  const [catalogError, setCatalogError] = useState(false)

  // bumped by "Try again" to re-run the fetch
  const [catalogAttempt, setCatalogAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    authFetch('/api/skins')
      .then((res) => {
        if (!res.ok) throw new Error(`Server returned status: ${res.status}`)
        return res.json()
      })
      .then((data) => {
        if (!cancelled) setCatalog(buildCatalog(data.skins.map((s) => s.market_hash_name)))
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof SessionExpiredError) {
          navigate('/login', { replace: true })
          return
        }
        setCatalogError(true)
      })
    return () => {
      cancelled = true
    }
  }, [catalogAttempt, navigate])

  const retryCatalog = () => {
    setCatalogError(false)
    setCatalogAttempt((n) => n + 1)
  }

  // Persisting here means the list survives a refresh and the login
  // redirect, neither of which router state does.
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist))
    } catch {
      // storage full or blocked: the list still works for this session 
    }
  }, [watchlist])

  // Once the typed finish matches a real skin, grey out the wears it
  // isn't tracked in so the dropdown shows what's available.
  const tracked = catalog && weapon ? variantsOf(catalog, weapon, finish) : []
  const trackedWears = new Set(
    tracked.filter((s) => s.statTrak === statTrak).map((s) => s.wear),
  )

  const handleAddItem = (e) => {
    e.preventDefault()
    setMessage('')
    setError('')
    if (!catalog) return

    const result = resolveSkin(catalog, { weapon, finish, wear, statTrak })
    if (result.error) {
      setError(result.error)
      return
    }

    if (watchlist.includes(result.name)) {
      setMessage('That skin is already on your watchlist.')
      return
    }

    setWatchlist([...watchlist, result.name])
    setFinish('')
  }

  const handleRemoveItem = (skin) => {
    setMessage('')
    setError('')
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

      {error && (
        <div className="app-error" role="alert">
          <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
            <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="M8 4.5v4.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            <circle cx="8" cy="11.4" r="0.9" fill="currentColor" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {catalogError && (
        <div className="app-error" role="alert">
          <span>
            Couldn't load the list of tracked skins.{' '}
            <button type="button" className="app-link" onClick={retryCatalog}>
              Try again
            </button>
          </span>
        </div>
      )}

      <form className="app-add" onSubmit={handleAddItem}>
        <select
          aria-label="Weapon"
          value={weapon}
          onChange={(e) => setWeapon(e.target.value)}
          disabled={!catalog}
        >
          <option value="">{catalog ? 'Weapon' : 'Loading…'}</option>
          {catalog && (
            <>
              <optgroup label="Guns">
                {catalog.guns.map((w) => <option key={w} value={w}>{w}</option>)}
              </optgroup>
              {catalog.knives.length > 0 && (
                <optgroup label="Knives">
                  {catalog.knives.map((w) => <option key={w} value={w}>★ {w}</option>)}
                </optgroup>
              )}
            </>
          )}
        </select>
        <input
          type="text"
          aria-label="Skin name"
          placeholder={weapon ? 'Skin, e.g. Redline' : 'Pick a weapon first'}
          list="finish-options"
          value={finish}
          onChange={(e) => setFinish(e.target.value)}
          disabled={!weapon}
        />
        <datalist id="finish-options">
          {(catalog?.finishes.get(weapon) || []).map((f) => (
            <option key={f} value={f} />
          ))}
        </datalist>
        <select
          aria-label="Wear"
          value={wear}
          onChange={(e) => setWear(e.target.value)}
        >
          {WEARS.map((w) => (
            <option key={w} value={w} disabled={tracked.length > 0 && !trackedWears.has(w)}>
              {w}
            </option>
          ))}
        </select>
        <label className="app-check">
          <input
            type="checkbox"
            checked={statTrak}
            onChange={(e) => setStatTrak(e.target.checked)}
          />
          StatTrak™
        </label>
        <button
          type="submit"
          className="app-button-secondary"
          disabled={!catalog || !weapon || !finish.trim()}
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
              <span className="app-item-name">
                {skin}
                {catalog && !catalog.names.has(skin) && (
                  <span className="app-tag app-tag-warn">No data</span>
                )}
              </span>
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