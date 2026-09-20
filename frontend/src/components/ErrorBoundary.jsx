import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an unhandled render error:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    } else {
      window.location.reload();
    }
  };

  handleClearCache = () => {
    try {
      sessionStorage.clear();
      window.location.reload();
    } catch {
      window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-card">
          <div className="error-boundary-icon">🧠⚠️</div>
          <h3 className="error-boundary-title">Something went wrong rendering this view</h3>
          <p className="error-boundary-msg">
            {this.state.error?.message || "An unexpected error occurred in the user interface."}
          </p>
          <div className="error-boundary-actions">
            <button className="btn primary" onClick={this.handleReset}>
              ↻ Reload Interface
            </button>
            <button className="btn" onClick={this.handleClearCache}>
              Reset Session Cache
            </button>
          </div>
          {this.state.error?.stack && (
            <details className="error-boundary-details">
              <summary>Technical Details</summary>
              <pre>{this.state.error.stack}</pre>
            </details>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
