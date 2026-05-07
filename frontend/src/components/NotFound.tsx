import { useNavigate } from 'react-router-dom';
import { Shield, ArrowLeft } from 'lucide-react';
import { Button } from './ui/button';

export default function NotFound() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100 p-6">
      <Shield className="h-12 w-12 text-slate-700 mb-6" />
      <p className="text-7xl font-black text-slate-800 mb-2">404</p>
      <h1 className="text-xl font-bold text-slate-300 mb-2">Page Not Found</h1>
      <p className="text-slate-500 text-sm mb-8 text-center max-w-sm">
        The page you're looking for doesn't exist or you may not have permission to access it.
      </p>
      <Button onClick={() => navigate('/')} className="bg-blue-600 hover:bg-blue-500 text-white">
        <ArrowLeft className="mr-2 h-4 w-4" /> Return to Dashboard
      </Button>
    </div>
  );
}
