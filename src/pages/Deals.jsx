import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

function Deals() {
  const location = useLocation()
  const navigate = useNavigate()
  
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [sortBy, setSortBy] = useState('best_deal') // Fixed typo: 'best_deal'
  const [skinQuery, setSkinQuery] = useState('')

  // Watchlist passed from Home page (or fallback default)
  const watchlist = location.state?.watchlist || ['AK-47 | Redline (Field-Tested)']

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
          limit: '20',
        })

        const response = await fetch(`http://127.0.0.1:8000/api/listings?${params.toString()}`)
        if (!response.ok) {
          throw new Error(`Server returned status: ${response.status}`)
        }

        const data = await response.json()
        const newListings = data.listings || []

        setListings((prevListings) => [...prevListings, ...newListings])
      }
    } catch (err) {
      setError('Could not connect to the backend. Make sure uvicorn is running on port 8000.')
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

  return (
    <div style={{ padding: '32px', maxWidth: '1000px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <button 
        onClick={() => navigate('/')} 
        style={{ marginBottom: '20px', padding: '8px 16px', cursor: 'pointer' }}
      >
        ← Back to Home
      </button>

      <h2>CS2 Skin Listings</h2>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px', marginBottom: '24px' }}>
        <input
          type="text"
          value={skinQuery}
          onChange={(e) => setSkinQuery(e.target.value)}
          placeholder="Search specific skin e.g. AWP | Asiimov (Field-Tested)"
          style={{ flex: 1, padding: '10px', fontSize: '14px' }}
        />
        <select 
          value={sortBy} 
          onChange={(e) => setSortBy(e.target.value)}
          style={{ padding: '10px', fontSize: '14px' }}
        >
          <option value="lowest_price">Lowest Price</option>
          <option value="most_recent">Most Recent</option>
          <option value="best_deal">Best Deal</option>
          <option value="lowest_float">Lowest Float</option>
        </select>
        <button type="submit" style={{ padding: '10px 20px', cursor: 'pointer' }}>
          Search
        </button>
      </form>

      {loading && <p style={{ color: '#2563eb' }}>Scanning CSFloat market listings...</p>}
      {error && <p style={{ color: '#ef4444' }}>{error}</p>}

      {!error && (
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ddd' }}>
              <th style={{ padding: '12px 8px' }}>Item</th>
              <th style={{ padding: '12px 8px' }}>Price</th>
              <th style={{ padding: '12px 8px' }}>Float Value</th>
              <th style={{ padding: '12px 8px' }}>Paint Seed</th>
              <th style={{ padding: '12px 8px' }}>Stickers</th>
              <th style={{ padding: '12px 8px' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {listings.length === 0 && !loading ? (
              <tr>
                <td colSpan="6" style={{ padding: '24px', textAlign: 'center', color: '#888' }}>
                  No active listings found for the specified items.
                </td>
              </tr>
            ) : (
              listings.map((item) => (
                <tr key={item.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '12px 8px', fontWeight: 600 }}>
                    {item.name}
                    {item.is_stattrak && (
                      <span style={{ marginLeft: '6px', color: '#ea580c', fontSize: '12px' }}>
                        [StatTrak™]
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '12px 8px', fontWeight: 700 }}>
                    ${item.price_usd.toFixed(2)}
                  </td>
                  <td style={{ padding: '12px 8px', fontFamily: 'monospace' }}>
                    {item.float_value !== null ? item.float_value.toFixed(5) : '—'}
                  </td>
                  <td style={{ padding: '12px 8px' }}>
                    {item.paint_seed || '—'}
                  </td>
                  <td style={{ padding: '12px 8px', fontSize: '12px', color: '#666' }}>
                    {item.stickers && item.stickers.length > 0 ? item.stickers.join(', ') : 'None'}
                  </td>
                  <td style={{ padding: '12px 8px' }}>
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        display: 'inline-block',
                        padding: '6px 12px',
                        background: '#22c55e',
                        color: '#fff',
                        textDecoration: 'none',
                        borderRadius: '4px',
                        fontSize: '13px',
                      }}
                    >
                      View
                    </a>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default Deals