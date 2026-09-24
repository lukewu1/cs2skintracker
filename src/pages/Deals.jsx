import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { authFetch, clearToken, SessionExpiredError } from '../auth'
import { loadWatchlist } from '../watchlist'
import './app.css'

function Deals() {
  const location = useLocation()
  const navigate = useNavigate()

  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sortBy, setSortBy] = useState('best_deal')
  const [skinQuery, setSkinQuery] = useState('')

  // Router state is lost on refresh, so fall back to the saved watchlist.
  const watchlist = location.state?.watchlist || loadWatchlist()

  // Function to fetch an array of skins
  const fetchWatchlistListings = async (itemsToFetch, sort) => {
    setLoading(true)
    setError(null)
    setListings([])

    try {
      for (let i = 0; i < itemsToFetch.length; i++) {
        const skinName = itemsToFetch[i]
        const params = new URLSearchParams({
          market_hash_name: skinName,
          sort_by: sort,
          limit: '5',
        })

        const response = await authFetch(`/api/listings?${params.toString()}`)
        if (!response.ok) {
          throw new Error(`Server returned status: ${response.status}`)
        }

        const data = await response.json()
        const newListings = data.listings || []

        setListings((prevListings) => [...prevListings, ...newListings])
      }
    } catch (err) {
      if (err instanceof SessionExpiredError) {
        navigate('/login', { replace: true })
        return
      }
      setError('Could not load listings. Check your connection and try again.')
    } finally {
      setLoading(false)
    }
  }

  // Fetch when page loads or when sortBy changes
  useEffect(() => {
    if (watchlist.length > 0) {
      fetchWatchlistListings(watchlist, sortBy)
    }
  }, [sortBy])

  // Handle manual single-item search
  const handleSubmit = (e) => {
    e.preventDefault()
    if (skinQuery.trim()) {
      fetchWatchlistListings([skinQuery.trim()], sortBy)
    }
  }

  const handleSignOut = () => {
    clearToken()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell app-shell-wide">
      <header className="app-header">
        <img src="/cs2skintracker.png" alt="" width="32" height="32" />
        <span className="app-wordmark">CS2 Skin Tracker</span>
        <div className="app-header-spacer" />
        <button type="button" className="app-link" onClick={() => navigate('/')}>
          ← Watchlist
        </button>
        <button type="button" className="app-link" onClick={handleSignOut}>
          Sign out
        </button>
      </header>

      <h1 className="app-title">Listings</h1>
      <p className="app-subtitle">
        The cheapest current CSFloat listings for each skin on your watchlist.
      </p>

      <form className="app-add" onSubmit={handleSubmit}>
        <input
          type="text"
          aria-label="Search one skin"
          value={skinQuery}
          onChange={(e) => setSkinQuery(e.target.value)}
          placeholder="Search one skin, e.g. AWP | Asiimov (Field-Tested)"
        />
        <select
          aria-label="Sort by"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="lowest_price">Lowest Price</option>
          <option value="most_recent">Most Recent</option>
          <option value="best_deal">Best Deal</option>
          <option value="lowest_float">Lowest Float</option>
        </select>
        <button type="submit" className="app-button-secondary">
          Search
        </button>
      </form>

      {loading && (
        <div className="app-status" role="status">
          <span className="app-spinner" aria-hidden="true" />
          Scanning CSFloat market listings…
        </div>
      )}

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

      {!error && (
        <div className="app-table-wrap">
          <table className="app-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Price</th>
                <th>Float Value</th>
                <th>Paint Seed</th>
                <th>Stickers</th>
                <th><span className="visually-hidden">Action</span></th>
              </tr>
            </thead>
            <tbody>
              {listings.length === 0 && !loading ? (
                <tr>
                  <td colSpan="6" className="app-cell-empty">
                    No listings found for these skins.
                  </td>
                </tr>
              ) : (
                listings.map((item) => (
                  <tr key={item.id}>
                    <td className="app-cell-name">
                      {item.name}
                      {item.is_stattrak && <span className="app-tag">StatTrak™</span>}
                    </td>
                    <td className="app-cell-price">${item.price_usd.toFixed(2)}</td>
                    <td className="app-cell-mono">
                      {item.float_value !== null ? item.float_value.toFixed(5) : '—'}
                    </td>
                    <td className="app-cell-mono">{item.paint_seed ?? '—'}</td>
                    <td className="app-cell-muted">
                      {item.stickers && item.stickers.length > 0 ? item.stickers.join(', ') : 'None'}
                    </td>
                    <td>
                      <a className="app-view" href={item.url} target="_blank" rel="noreferrer">
                        View
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default Deals
