import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('[ SYSTEM ERROR ] Uncaught exception:', error, errorInfo);
    }

    private handleReset = () => {
        this.setState({ hasError: false, error: null });
        window.location.reload();
    };

    public render() {
        if (this.state.hasError) {
            return (
                <div className="flex flex-col items-center justify-center min-h-[300px] p-8 glass-morphism rounded-xl border border-red-500/20 m-4">
                    <AlertCircle className="w-12 h-12 text-red-500 mb-4 animate-pulse" />
                    <h2 className="text-xl font-bold text-white mb-2">Manifold Instability Detected</h2>
                    <p className="text-gray-400 text-center mb-6 max-w-md">
                        A cognitive subsystem has collapsed. This may be due to a malformed soul manifest or transient manifold tearing.
                    </p>
                    <button
                        onClick={this.handleReset}
                        className="flex items-center gap-2 px-6 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/30 rounded-lg transition-all duration-300 font-medium"
                    >
                        <RotateCcw className="w-4 h-4" />
                        Recalibrate Initial State
                    </button>

                    {process.env.NODE_ENV === 'development' && (
                        <div className="mt-8 p-4 bg-black/40 rounded-lg border border-white/5 w-full overflow-hidden">
                            <p className="text-xs font-mono text-red-400 break-words line-clamp-4">
                                {this.state.error?.toString()}
                            </p>
                        </div>
                    )}
                </div>
            );
        }

        return this.props.children;
    }
}
