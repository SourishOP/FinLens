import { Component } from "react";

// Catches render-time exceptions in a subtree so one bad chart/report can't
// blank the whole app. Shows the error inline and lets the rest of the UI live.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Surface in the console for debugging; the UI still shows the message.
    // eslint-disable-next-line no-console
    console.error("Render error caught by ErrorBoundary:", error, info);
  }

  reset = () => this.setState({ error: null });

  componentDidUpdate(prevProps) {
    // Reset when the caller swaps content (e.g. a new tab is selected).
    if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
      this.reset();
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-xl bg-red-50 border border-red-100 text-red-700 text-sm p-4">
          <div className="font-semibold mb-1">This section couldn't be displayed.</div>
          <div className="text-red-600/80 text-xs break-words">
            {String(this.state.error?.message || this.state.error)}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
