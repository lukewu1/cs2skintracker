import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
// import './Home.css'

function Home() {
  const navigate = useNavigate()
  
  // State for the input box and the list of skins
  const [inputValue, setInputValue] = useState('')
  const [watchlist, setWatchlist] = useState([
    'AK-47 | Redline (Field-Tested)',
    'AWP | Asiimov (Field-Tested)'
  ])

  // Add item to list
  const handleAddItem = (e) => {
    e.preventDefault()
    const trimmed = inputValue.trim()
    if (trimmed && !watchlist.includes(trimmed)) {
      setWatchlist([...watchlist, trimmed])
      setInputValue('')
    }
  }

  // Remove single item
  const handleRemoveItem = (indexToRemove) => {
    setWatchlist(watchlist.filter((_, idx) => idx !== indexToRemove))
  }

  // Navigate to Deals page and pass the user's custom watchlist
  const handleScan = () => {
    if (watchlist.length === 0) {
      alert('Please add at least one skin to scan.')
      return
    }
    navigate('/deals', { state: { watchlist } })
  }

  return (
    <div style={{ padding: '32px', maxWidth: '600px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <h2>CS2 Skin Tracker</h2>
      <p style={{ color: '#666' }}>Enter a list of skins you would like to scan on CSFloat:</p>

      {/* Input + Add Button */}
      <form onSubmit={handleAddItem} style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
        <input
          type="text"
          placeholder="e.g. Desert Eagle | Printstream (Field-Tested)"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          style={{ flex: 1, padding: '10px', fontSize: '14px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <button 
          type="submit" 
          style={{ padding: '10px 18px', cursor: 'pointer', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '4px', fontWeight: 600 }}
        >
          Add Item
        </button>
      </form>

      {/* Watchlist Display */}
      <ul style={{ listStyle: 'none', padding: 0, marginBottom: '24px' }}>
        {watchlist.map((skin, index) => (
          <li
            key={index}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '10px 12px',
              marginBottom: '8px',
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '6px'
            }}
          >
            <span style={{ fontWeight: 500 }}>{skin}</span>
            <button
              type="button"
              onClick={() => handleRemoveItem(index)}
              style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontWeight: 'bold' }}
            >
              ✕
            </button>
          </li>
        ))}
      </ul>

      {/* Scan Button */}
      <button 
        type="button"
        onClick={handleScan} 
        style={{
          width: '100%',
          padding: '12px',
          background: '#22c55e',
          color: '#fff',
          border: 'none',
          borderRadius: '6px',
          fontSize: '16px',
          fontWeight: 600,
          cursor: 'pointer'
        }}
      >
        Scan Deals ({watchlist.length} items)
      </button>
    </div>
  )
}

export default Home