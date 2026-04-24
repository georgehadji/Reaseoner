'use client';

import { useRef, useCallback, useEffect, useState } from 'react';
import { PhaseEvent } from '@/lib/types';
import { WS } from '@/lib/config';
import { REASONER_WS_URL } from '@/lib/server-config';

export type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

export function useWebSocketPipeline() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onEventRef = useRef<((ev: PhaseEvent) => void) | null>(null);
  const pipelineIdRef = useRef<string | null>(null);

  const [status, setStatus] = useState<ConnectionStatus>('idle');

  const clearReconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const doConnect = useCallback((pipelineId: string, onEvent: (ev: PhaseEvent) => void) => {
    clearReconnect();
    pipelineIdRef.current = pipelineId;
    onEventRef.current = onEvent;

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setStatus('connecting');
    const ws = new WebSocket(`${REASONER_WS_URL}?pipeline_id=${encodeURIComponent(pipelineId)}`);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectCountRef.current = 0;
      setStatus('connected');
      // eslint-disable-next-line no-console
      console.debug('[WebSocket] connected for pipeline:', pipelineId);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'event' && msg.data && onEventRef.current) {
          onEventRef.current(msg.data as PhaseEvent);
        }
      } catch {
        // ignore malformed messages
      }
    };

    ws.onerror = (err) => {
      // eslint-disable-next-line no-console
      console.error('[WebSocket] error:', err);
    };

    ws.onclose = () => {
      wsRef.current = null;
      const currentPipelineId = pipelineIdRef.current;

      // Only attempt reconnect if we still care about this pipeline
      if (currentPipelineId === pipelineId && reconnectCountRef.current < WS.maxReconnectAttempts) {
        reconnectCountRef.current += 1;
        const delay = WS.baseReconnectDelayMs * Math.pow(2, reconnectCountRef.current - 1);
        setStatus('reconnecting');
        // eslint-disable-next-line no-console
        console.debug(`[WebSocket] reconnecting in ${delay}ms (attempt ${reconnectCountRef.current})`);
        reconnectTimerRef.current = setTimeout(() => {
          if (onEventRef.current) doConnect(pipelineId, onEventRef.current);
        }, delay);
      } else {
        setStatus('disconnected');
      }
    };
  }, [clearReconnect]);

  const connect = useCallback((pipelineId: string, onEvent: (ev: PhaseEvent) => void) => {
    reconnectCountRef.current = 0;
    doConnect(pipelineId, onEvent);
  }, [doConnect]);

  const disconnect = useCallback(() => {
    clearReconnect();
    pipelineIdRef.current = null;
    onEventRef.current = null;
    reconnectCountRef.current = 0;

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setStatus('idle');
  }, [clearReconnect]);

  const sendStop = useCallback((pipelineId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: 'stop', pipeline_id: pipelineId })
      );
    }
  }, []);

  useEffect(() => {
    return () => {
      clearReconnect();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [clearReconnect]);

  return { connect, disconnect, sendStop, status };
}
