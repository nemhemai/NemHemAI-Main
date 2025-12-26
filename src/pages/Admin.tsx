import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUserInfo, isAuthenticated } from '@/lib/api';

const Admin = () => {
  const [user, setUser] = useState<{ sub: string; role: string } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/login');
      return;
    }
    const info = getUserInfo();
    if (!info || info.role !== 'admin') {
      navigate('/');
      return;
    }
    setUser(info);
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="w-full max-w-lg bg-slate-900/80 rounded-2xl shadow-2xl p-8 border border-slate-700/50">
        <h2 className="text-2xl font-bold text-center bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 bg-clip-text text-transparent mb-6">
          Admin Panel
        </h2>
        <div className="text-slate-300 text-center mb-4">
          Welcome, <span className="text-emerald-400 font-semibold">{user?.sub}</span>!<br />
          <span className="text-xs text-slate-400">Role: {user?.role}</span>
        </div>
        <div className="text-slate-400 text-center">
          <p>This is a protected admin-only area. You can add admin features here.</p>
        </div>
      </div>
    </div>
  );
};

export default Admin; 