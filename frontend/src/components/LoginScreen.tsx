import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, Lock, AlertCircle, Loader2, Eye, EyeOff, ExternalLink, Activity } from 'lucide-react';
import { GlassCard } from './ui/GlassCard';
import { NeonButton } from './ui/NeonButton';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { useTheme } from '../lib/useTheme';
import { motion } from 'framer-motion';

export default function LoginScreen() {
  const navigate = useNavigate();
  const location  = useLocation();

  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw]     = useState(false);
  const [error, setError]       = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);
  const { theme } = useTheme();

  // Show a contextual message if the user was redirected here (e.g., expired session)
  const sessionExpired = new URLSearchParams(location.search).get('reason') === 'expired'
    || (location.state as any)?.sessionExpired === true;

  // Redirect away if already authenticated
  useEffect(() => {
    if (localStorage.getItem('token')) {
      navigate('/', { replace: true });
    }
  }, [navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email.trim());
      formData.append('password', password);

      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData,
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(data.detail || 'Incorrect email or password. Please try again.');
      }

      const data = await res.json();
      localStorage.setItem('token', data.access_token);

      if (data.force_password_change) {
        localStorage.setItem('force_password_change', 'true');
      } else {
        localStorage.removeItem('force_password_change');
      }

      navigate('/', { replace: true });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050B18] flex flex-col items-center justify-center p-4 relative overflow-hidden text-white">
      
      {/* Background Animated Glows - ARKA PLAN PARLAMALARI */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-[#00F2FF]/10 rounded-full blur-[150px] animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] bg-[#7000FF]/10 rounded-full blur-[150px] animate-pulse" style={{ animationDelay: '2s' }} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="text-center mb-8 space-y-2">
           <div className="flex items-center justify-center gap-3 mb-4">
              <Shield className="w-12 h-12 text-[#00F2FF] filter drop-shadow-[0_0_10px_rgba(0,242,255,0.8)]" />
              <h1 className="text-4xl font-black tracking-tighter uppercase italic text-white">
                RALPH <span className="text-[#00F2FF]">LOOP</span>
              </h1>
           </div>
           <p className="text-slate-400 text-xs font-mono tracking-[0.3em] flex items-center justify-center gap-2">
              <Activity className="w-3 h-3 text-[#10B981]" /> SECURE ACCESS PORTAL
           </p>
        </div>

        {/* 3D Glass Card - GERÇEK 3D CAM KART */}
        <div 
          className="rounded-3xl p-8 relative overflow-hidden border border-white/10 shadow-[0_40px_100px_rgba(0,0,0,0.8)]"
          style={{ 
            background: 'linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))',
            backdropFilter: 'blur(30px)',
            transform: 'perspective(1000px) rotateX(2deg)',
            boxShadow: '0 0 20px rgba(0,242,255,0.05)'
          }}
        >
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-bold text-white tracking-[0.2em] uppercase">
                AUTHENTICATION
              </h2>
              <div className="h-0.5 w-16 bg-[#00F2FF] mx-auto mt-2" />
            </div>

            <form onSubmit={handleLogin} className="space-y-5" noValidate>
              <div className="space-y-2">
                <Label className="text-slate-400 text-[10px] uppercase font-bold tracking-widest ml-1">Email Address</Label>
                <input
                  type="email"
                  placeholder="admin@ralphloop.io"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl py-4 px-4 text-white focus:outline-none focus:border-[#00F2FF] transition-all placeholder:text-slate-700"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-400 text-[10px] uppercase font-bold tracking-widest ml-1">Password</Label>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl py-4 px-4 text-white focus:outline-none focus:border-[#00F2FF] transition-all placeholder:text-slate-700 pr-12"
                    required
                  />
                  <button
                    type="button"
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-[#00F2FF]"
                    onClick={() => setShowPw(v => !v)}
                  >
                    {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-4 bg-[#00F2FF] text-[#050B18] font-black uppercase tracking-[0.2em] rounded-xl hover:bg-[#00F2FF]/90 transition-all hover:scale-[1.02] shadow-[0_0_20px_rgba(0,242,255,0.3)] mt-4"
                disabled={loading}
              >
                {loading ? 'AUTHENTICATING...' : 'INITIATE LOGIN'}
              </button>
            </form>
          </div>
        </div>

        <div className="mt-8 flex flex-col items-center gap-4">
           {/* Footer links */}
           <div className="flex items-center gap-6 text-[10px] text-slate-500 font-bold tracking-widest uppercase">
              {theme.platform.privacyPolicyUrl && (
                <a href={theme.platform.privacyPolicyUrl} target="_blank" rel="noopener noreferrer" className="hover:text-cyber-cyan transition-colors">
                  Privacy
                </a>
              )}
              {theme.platform.termsUrl && (
                <a href={theme.platform.termsUrl} target="_blank" rel="noopener noreferrer" className="hover:text-cyber-cyan transition-colors">
                  Terms
                </a>
              )}
              {theme.platform.supportEmail && (
                <a href={`mailto:${theme.platform.supportEmail}`} className="hover:text-cyber-cyan transition-colors">
                  Support
                </a>
              )}
           </div>
           
           <p className="text-[10px] text-slate-700 font-mono italic">
              {theme.platform.name} v{theme.platform.version} // {theme.platform.copyrightHolder}
           </p>
        </div>
      </motion.div>
    </div>
  );
}
