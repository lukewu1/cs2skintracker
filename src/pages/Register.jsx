import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './auth.css';

export default function RegisterForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Both passwords need to match.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: email, password }),
      });

      if (res.status === 409) {
        setError('That email already has an account. Sign in instead.');
        return;
      }
      if (!res.ok) {
        setError('The account could not be created. Try again in a moment.');
        return;
      }

      navigate('/login');
    } catch {
      setError('Cannot reach the server. Check your connection and try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <aside className="auth-aside">
        <span className="auth-wordmark">Your app</span>
        <div>
          <p className="auth-aside-copy">Everything you save, in one place.</p>
          <p className="auth-aside-note">
            Your account keeps your work synced across every device you sign in on.
          </p>
        </div>
      </aside>

      <main className="auth-main">
        <form className="auth-form" onSubmit={handleSubmit} noValidate={false}>
          <h1 className="auth-title">Create your account</h1>
          <p className="auth-subtitle">
            Already have one? <Link to="/login">Sign in</Link>
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
            <label htmlFor="register-email">Email</label>
            <input
              type="email"
              id="register-email"
              name="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="register-password">Password</label>
            <input
              type="password"
              id="register-password"
              name="new-password"
              autoComplete="new-password"
              placeholder="At least 8 characters"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="register-confirm">Confirm password</label>
            <input
              type="password"
              id="register-confirm"
              name="confirm-password"
              autoComplete="new-password"
              placeholder="Type it once more"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          <button type="submit" className="auth-button" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>
      </main>
    </div>
  );
}