import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
// import './Login.css';

export default function LoginForm(){
    const [email, setEmail] = useState({email: ''});
    const [password, setPassword] = useState({password: ''});
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        try {
            const res = await fetch('http://localhost:8000/api/auth/token', {
                method: 'POST',
                body: new URLSearchParams({ username: email, password }),
            });

            if (!res.ok) {
                setError('Invalid email or password');
                return;
            }

            const data = await res.json();
            localStorage.setItem('token', data.access_token);
            navigate('/')
        } catch {
            setError('Could not reach the server');
        }
    };

    return(
        <div className='logincontainer'>
            <form className='loginform' onSubmit={handleSubmit}>
                <h2 className='formtitle'>Login</h2>
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
                <button type='submit' className='submitbtn'>Login</button>
            </form>
        </div>
    )
}