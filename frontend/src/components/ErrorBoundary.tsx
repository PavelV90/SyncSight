import { Component, type ReactNode } from "react";

type Props = { children: ReactNode; name: string };
type State = { failed: boolean };

/** Keeps one broken view from blanking the whole app. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div role="alert" className="status status--error">
        <span>{this.props.name} could not be displayed.</span>
        <button type="button" onClick={() => this.setState({ failed: false })}>
          Try again
        </button>
      </div>
    );
  }
}
