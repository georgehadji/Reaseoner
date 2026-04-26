'use client';

import { Component, ReactNode } from 'react';

interface ChatErrorBoundaryProps {
  fallback: ReactNode;
  children: ReactNode;
}

interface ChatErrorBoundaryState {
  hasError: boolean;
}

export class ChatErrorBoundary extends Component<
  ChatErrorBoundaryProps,
  ChatErrorBoundaryState
> {
  state = { hasError: false };

  static getDerivedStateFromError(): ChatErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error('Chat render error:', error);
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}
