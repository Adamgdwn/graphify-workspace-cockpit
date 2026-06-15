import { Component, type ReactNode, type ErrorInfo } from "react";

interface Props {
  children: ReactNode;
  tabName: string;
}

interface State {
  hasError: boolean;
  error: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`Tab "${this.props.tabName}" error:`, error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-fallback">
          <span className="error-boundary-icon">⚠</span>
          <p className="error-boundary-title">This tab encountered an error — refresh to retry</p>
          {this.state.error && (
            <p className="error-boundary-sub">{this.state.error}</p>
          )}
          <button
            className="error-boundary-btn"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
