import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
// import './Login.css';

export default function RegisterForm(){
    const [email, setEmail] = useState({email: ''});
    const [password, setPassword] = useState({password: ''});
    const [confirmPassword, setConfirmedPassword] = useState({confirmedPassword: ''});
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        try {
            const res = await fetch('http://localhost:8000/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: email, password }),
            });

            if (res.status === 409) {
                setError('That email is already registered');
                return;
            }
            if (!res.ok) {
                setError('Registration failed');
                return;
            }

            navigate('/login');
        } catch {
            setError('Could not reach the server');
        }
    };

    return(
        <div className='logincontainer'>
            <form className='loginform' onSubmit={handleSubmit}>
                <h2 className='formtitle'>Register</h2>
                <div className='formgroup'>
                    <label htmlFor='email'>Email</label>
                    <input
                        type='email'
                        id='email'
                        placeholder='Enter Your Email'
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                </div>
                <div className='formgroup'>
                    <label htmlFor='password'>Password</label>
                    <input
                        type='password'
                        id='password'
                        placeholder='Enter Your Password'
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                </div>
                <div className='formgroup'>
                    <label htmlFor='password'>Confirm Password</label>
                    <input
                        type='password'
                        id='confirmPassword'
                        placeholder='Confirm Your Password'
                        value={confirmPassword}
                        onChange={(e) => setConfirmedPassword(e.target.value)}
                        required
                    />
                </div>
                <button type='submit' className='submitbtn'>Register</button>
            </form>
        </div>
    )
}