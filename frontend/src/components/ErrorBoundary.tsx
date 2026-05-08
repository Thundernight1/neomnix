/**
 * ErrorBoundary — Global React error boundary.
 *
 * Catches unhandled JavaScript errors in the component tree and displays
 * a graceful fallback screen instead of a blank white page.
 * Required for enterprise production deployments.
 */

import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    // In production, send to your error monitoring service here
    console.error('[Neomnix GRC] Unhandled error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
          <Card className="bg-slate-900 border-red-900/50 max-w-md w-full text-center shadow-2xl shadow-red-900/10">
            <CardContent className="pt-12 pb-10 flex flex-col items-center gap-5">
              <div className="w-16 h-16 rounded-full bg-red-950/60 border border-red-800 flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-red-400" />
              </div>
              <div className="space-y-2">
                <h2 className="text-xl font-bold text-white">Something went wrong</h2>
                <p className="text-slate-400 text-sm leading-relaxed">
                  An unexpected error occurred. Your data is safe — this is a display error only.
                  Click below to return to the dashboard.
                </p>
              </div>
              {import.meta.env.DEV && this.state.error && (
                <pre className="text-left text-[10px] text-red-400 bg-black/40 p-3 rounded w-full overflow-x-auto max-h-32">
                  {this.state.error.toString()}
                </pre>
              )}
              <Button
                onClick={this.handleReset}
                className="bg-blue-600 hover:bg-blue-500 text-white font-semibold"
              >
                <RefreshCw className="mr-2 h-4 w-4" /> Return to Dashboard
              </Button>
              <p className="text-[10px] text-slate-600">
                If this problem persists, contact your platform administrator.
              </p>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
