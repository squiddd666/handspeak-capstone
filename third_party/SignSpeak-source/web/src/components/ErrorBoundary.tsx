import React from "react";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches render errors anywhere in the app and shows a recovery card instead
 * of unmounting to a blank screen.
 */
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Unhandled render error:", error, info.componentStack);
  }

  private goHome = () => {
    window.location.href = "/";
  };

  private reload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center px-4 bg-background text-foreground">
          <div className="panel-card max-w-md w-full p-6 sm:p-8 text-center space-y-5 border-2 border-destructive/30">
            <div className="flex justify-center">
              <div className="p-4 bg-destructive/10 rounded-full text-destructive">
                <AlertTriangle className="w-10 h-10" aria-hidden="true" />
              </div>
            </div>
            <div className="space-y-2">
              <h1 className="text-xl font-semibold">Something went wrong</h1>
              <p className="text-sm text-muted-foreground">
                An unexpected error occurred on this screen. Your data is safe —
                reload or head back home to continue.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={this.reload}
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border-2 border-primary/30 hover:border-primary text-sm font-semibold transition-colors"
              >
                <RotateCcw className="w-4 h-4" aria-hidden="true" /> Reload
              </button>
              <button
                onClick={this.goHome}
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:opacity-90 transition-opacity"
              >
                <Home className="w-4 h-4" aria-hidden="true" /> Home
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
