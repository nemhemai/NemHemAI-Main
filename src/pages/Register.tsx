import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { API_BASE_URL } from '@/lib/api';

const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!response.ok) {
        const data = await response.json();
        if (data.detail && data.detail.includes('Username already registered')) {
          setError('Username already exists. Please choose another.');
        } else {
          setError(data.detail || 'Registration failed');
        }
        setLoading(false);
        return;
      }
      navigate('/login');
    } catch (err) {
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#1b142d] via-[#1c152d] to-[#1b142d]">
      <div className="w-full max-w-md bg-[#1f1833] rounded-2xl shadow-2xl p-8 border border-[#342e4e]">
        <h2 className="text-2xl font-bold text-center text-white mb-6">
          Register for NemHem AI
        </h2>
        <form onSubmit={handleRegister} className="space-y-6">
          <div>
            <label className="block text-slate-300 text-sm font-medium mb-2">Username</label>
            <Input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="bg-[#2c2344] border border-[#4c3e72] text-white placeholder-slate-400 focus:ring-purple-500 focus:border-purple-500"
              required
              autoFocus
            />
          </div>
          <div>
            <label className="block text-slate-300 text-sm font-medium mb-2">Password</label>
            <Input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="bg-[#2c2344] border border-[#4c3e72] text-white placeholder-slate-400 focus:ring-purple-500 focus:border-purple-500"
              required
            />
          </div>
          <div>
            <label className="block text-slate-300 text-sm font-medium mb-2">Confirm Password</label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              className="bg-[#2c2344] border border-[#4c3e72] text-white placeholder-slate-400 focus:ring-purple-500 focus:border-purple-500"
              required
            />
          </div>
          {error && <div className="text-red-400 text-sm text-center">{error}</div>}
          <Button
            type="submit"
            className="w-full bg-gradient-to-r from-[#a45cf6] to-[#805efc] hover:from-[#9552f2] hover:to-[#724dea] text-white border-0 h-[40px] rounded-2xl shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={loading}
          >
            {loading ? 'Registering...' : 'Register'}
          </Button>
        </form>
        <div className="mt-6 text-center">
          <span className="text-slate-400 text-sm">Already have an account? </span>
          <Link to="/login" className="text-[#a45cf6] hover:underline">Login</Link>
        </div>
      </div>
    </div>
  );
};

export default Register;
