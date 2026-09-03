import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { setToken, API_URL } from '../auth';
import './auth.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      const res = await fetch(`${API_URL}/api/auth/token`, {
        method: 'POST',
        body: new URLSearchParams({ username: email, password }),
      });

      if (res.status === 401) {
        setError('That email and password do not match an account.');
        return;
      }
      if (!res.ok) {
        setError('Something went wrong signing in. Try again.');
        return;
      }

      const data = await res.json();
      setToken(data.access_token);
      navigate(from, { replace: true });
    } catch {
      setError('Cannot reach the server. Check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <aside className="auth-aside">
        <div className="auth-logo">
          <img src="/cs2skintracker.png" alt="" width="40" height="40" />
          <span className="auth-wordmark">CS2 Skin Tracker</span>
        </div>

        <div>
          <p className="auth-aside-copy">Watch the market so you don't have to.</p>
          <ul className="auth-points">
            <li>Live CSFloat listings, filtered by float and price</li>
            <li>Watchlists tied to your account, not your browser</li>
            <li>Cached scans, so repeat searches return instantly</li>
          </ul>
        </div>
      </aside>

      <main className="auth-main">
        <form className="auth-form" onSubmit={handleSubmit}>
          <h1 className="auth-title">Sign in</h1>
          <p className="auth-subtitle">
            New here? <Link to="/register">Create an account</Link>
          </p>

          {error && (
            <div className="auth-error" role="alert">
              <svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true">
                <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.5" />
                <path d="M8 4.5v4.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <circle cx="8" cy="11.4" r="0.9" fill="currentColor" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <div className="auth-field">
            <label htmlFor="login-email">Email</label>
            <input
              type="email"
              id="login-email"
              name="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="login-password">Password</label>
            <input
              type="password"
              id="login-password"
              name="password"
              autoComplete="current-password"
              placeholder="Your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="auth-button" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </main>
    </div>
  );
}