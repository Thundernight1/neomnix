/**
 * ForcePasswordChangeModal — First-Login Security Gate
 *
 * Blocking modal enforcing a password change for any account provisioned
 * with a temporary password. Cannot be dismissed without completing the change.
 * Respects theme.json branding colors.
 */

import { useState } from 'react';
import { ShieldAlert, Lock, Eye, EyeOff, CheckCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Alert, AlertDescription } from './ui/alert';
import { useTheme } from '../lib/useTheme';

interface Props {
  onPasswordChanged: () => void;
}

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const REQUIREMENTS = [
  { label: 'At least 10 characters',  test: (pw: string) => pw.length >= 10 },
  { label: 'One uppercase letter',     test: (pw: string) => /[A-Z]/.test(pw) },
  { label: 'One number',              test: (pw: string) => /[0-9]/.test(pw) },
  { label: 'One special character',   test: (pw: string) => /[^A-Za-z0-9]/.test(pw) },
];

function passwordScore(pw: string): number {
  return [pw.length >= 10, pw.length >= 14, /[A-Z]/.test(pw), /[0-9]/.test(pw), /[^A-Za-z0-9]/.test(pw)]
    .filter(Boolean).length;
}

const STRENGTH_LABELS = ['', 'Weak', 'Fair', 'Good', 'Strong', 'Excellent'];
const STRENGTH_COLORS = ['', 'text-red-400', 'text-yellow-400', 'text-blue-400', 'text-green-400', 'text-green-300'];
const BAR_COLORS      = ['', 'bg-red-500', 'bg-yellow-400', 'bg-blue-400', 'bg-green-400', 'bg-green-300'];

export default function ForcePasswordChangeModal({ onPasswordChanged }: Props) {
  const { theme } = useTheme();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword,     setNewPassword]     = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent,     setShowCurrent]     = useState(false);
  const [showNew,         setShowNew]         = useState(false);
  const [showConfirm,     setShowConfirm]     = useState(false);
  const [loading,         setLoading]         = useState(false);
  const [error,           setError]           = useState<string | null>(null);
  const [success,         setSuccess]         = useState(false);

  const score = passwordScore(newPassword);
  const allRequirementsMet = REQUIREMENTS.every(r => r.test(newPassword));
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.');
      return;
    }
    if (!allRequirementsMet) {
      setError('Password does not meet all requirements below.');
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE}/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: 'Password change failed' }));
        throw new Error(data.detail || 'Password change failed.');
      }

      localStorage.removeItem('force_password_change');
      setSuccess(true);
      setTimeout(() => onPasswordChanged(), 2000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const primaryColor = theme.branding.primaryColor || '#3b82f6';

  return (
    <div className="fixed inset-0 bg-slate-950/95 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-slate-900 border-amber-800/50 text-slate-100 shadow-2xl shadow-amber-900/10">
        <CardHeader className="text-center space-y-3 pt-7">
          <div className="mx-auto w-14 h-14 bg-amber-900/30 rounded-full flex items-center justify-center ring-2 ring-amber-700/40">
            <ShieldAlert className="w-7 h-7 text-amber-400" />
          </div>
          <CardTitle className="text-xl font-bold text-white">
            {success ? 'Password Updated' : 'Security Action Required'}
          </CardTitle>
          <CardDescription className="text-slate-400 text-sm leading-relaxed">
            {success
              ? `Your account is secured. Redirecting to ${theme.platform.shortName}…`
              : `Your account on ${theme.platform.name} was provisioned with a temporary password. Set a permanent password to continue.`
            }
          </CardDescription>
        </CardHeader>

        <CardContent className="pb-6">
          {success ? (
            <div className="flex flex-col items-center gap-4 py-6">
              <CheckCircle className="w-16 h-16 text-green-400" />
              <p className="text-slate-300 text-sm text-center">
                Your credentials are secured and your session is active.
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">

              {/* Current password */}
              <div className="space-y-1.5">
                <Label htmlFor="current-pw" className="text-slate-300 text-xs uppercase tracking-wide">
                  Current (Temporary) Password
                </Label>
                <div className="relative">
                  <Input
                    id="current-pw"
                    type={showCurrent ? 'text' : 'password'}
                    autoComplete="current-password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="bg-slate-950 border-slate-700 pr-10"
                    placeholder="Enter your current password"
                    required autoFocus
                  />
                  <button type="button" aria-label={showCurrent ? 'Hide' : 'Show'} aria-pressed={showCurrent}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    onClick={() => setShowCurrent(v => !v)}>
                    {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* New password */}
              <div className="space-y-1.5">
                <Label htmlFor="new-pw" className="text-slate-300 text-xs uppercase tracking-wide">
                  New Password
                </Label>
                <div className="relative">
                  <Input
                    id="new-pw"
                    type={showNew ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="bg-slate-950 border-slate-700 pr-10"
                    placeholder="Minimum 10 characters"
                    required
                  />
                  <button type="button" aria-label={showNew ? 'Hide' : 'Show'} aria-pressed={showNew}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    onClick={() => setShowNew(v => !v)}>
                    {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>

                {/* Strength meter */}
                {newPassword.length > 0 && (
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex gap-1 flex-1">
                      {[1, 2, 3, 4, 5].map(i => (
                        <div key={i} className={`h-1 flex-1 rounded-full transition-all duration-200 ${i <= score ? BAR_COLORS[score] : 'bg-slate-700'}`} />
                      ))}
                    </div>
                    <span className={`text-xs font-medium ${STRENGTH_COLORS[score]}`}>
                      {STRENGTH_LABELS[score]}
                    </span>
                  </div>
                )}
              </div>

              {/* Confirm password */}
              <div className="space-y-1.5">
                <Label htmlFor="confirm-pw" className="text-slate-300 text-xs uppercase tracking-wide">
                  Confirm New Password
                </Label>
                <div className="relative">
                  <Input
                    id="confirm-pw"
                    type={showConfirm ? 'text' : 'password'}
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className={`bg-slate-950 border-slate-700 pr-10 ${
                      confirmPassword.length > 0 ? (passwordsMatch ? 'border-green-700' : 'border-red-700') : ''
                    }`}
                    placeholder="Re-enter new password"
                    required
                  />
                  <button type="button" aria-label={showConfirm ? 'Hide' : 'Show'} aria-pressed={showConfirm}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    onClick={() => setShowConfirm(v => !v)}>
                    {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {confirmPassword.length > 0 && !passwordsMatch && (
                  <p className="text-xs text-red-400">Passwords do not match</p>
                )}
              </div>

              {/* Requirements checklist */}
              <div className="bg-slate-800/50 rounded-lg p-3 space-y-1 border border-slate-700">
                <p className="text-xs font-medium text-slate-300 flex items-center gap-1 mb-2">
                  <Lock className="h-3 w-3" /> Requirements
                </p>
                {REQUIREMENTS.map(({ label, test }) => {
                  const met = test(newPassword);
                  return (
                    <div key={label} className={`flex items-center gap-2 text-xs ${met ? 'text-green-400' : 'text-slate-500'}`}>
                      <span className="w-3 text-center">{met ? '✓' : '○'}</span>
                      {label}
                    </div>
                  );
                })}
              </div>

              {error && (
                <Alert className="bg-red-900/20 border-red-800 text-red-200">
                  <AlertDescription className="text-sm">{error}</AlertDescription>
                </Alert>
              )}

              <Button
                type="submit"
                disabled={loading || !allRequirementsMet || !passwordsMatch || !currentPassword}
                className="w-full font-semibold text-white"
                style={{ backgroundColor: primaryColor }}
              >
                {loading
                  ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Securing Account…</>
                  : <><Lock className="mr-2 h-4 w-4" /> Set Password &amp; Continue</>
                }
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
