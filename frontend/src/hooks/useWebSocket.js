import { useEffect, useRef, useState, useCallback } from 'react';
import { getWebSocketURL, alertsAPI } from '../api/client';

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000];

/**
 * useWebSocket - manages a stable WebSocket connection to the backend alerts stream.
 * Falls back to HTTP polling every 8s if WebSocket fails repeatedly.
 * @param {function} onMessage - called with each parsed alert object
 */
export function useWebSocket(onMessage) {
  const wsRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef(null);
  const pollTimer = useRef(null);
  const lastAlertId = useRef(0);
  const mountedRef = useRef(true);
  const [status, setStatus] = useState('disconnected'); // 'connecting' | 'connected' | 'disconnected' | 'polling'

  // Keep latest onMessage callback without triggering re-connections
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    if (pollTimer.current) return;
    setStatus('polling');
    const poll = async () => {
      try {
        const { data } = await alertsAPI.latest();
        const alerts = Array.isArray(data) ? data : data.alerts || [];
        alerts.forEach((alert) => {
          if (alert.id > lastAlertId.current) {
            lastAlertId.current = alert.id;
            onMessageRef.current?.(alert);
          }
        });
      } catch { /* ignore poll errors */ }
      if (mountedRef.current) {
        pollTimer.current = setTimeout(poll, 8000);
      }
    };
    poll();
  }, []);

  const connect = useCallback(() => {
    if (!localStorage.getItem('access_token')) return;

    // Do not reconnect if already open or connecting
    const current = wsRef.current;
    if (current && (current.readyState === WebSocket.OPEN || current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    setStatus('connecting');
    const url = getWebSocketURL();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close();
        return;
      }
      reconnectAttempts.current = 0;
      setStatus('connected');
      stopPolling();
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'NEW_ALERT') {
          onMessageRef.current?.(data);
          lastAlertId.current = Math.max(lastAlertId.current, data.alert_id || 0);
        }
      } catch { /* ignore parse errors */ }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setStatus('disconnected');
      const attempt = reconnectAttempts.current;
      if (attempt < RECONNECT_DELAYS.length) {
        const delay = RECONNECT_DELAYS[attempt];
        reconnectAttempts.current += 1;
        reconnectTimer.current = setTimeout(connect, delay);
      } else {
        // Fall back to polling
        startPolling();
      }
    };

    ws.onerror = () => {
      // Browser handles close event automatically
    };
  }, [startPolling, stopPolling]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
      }
      stopPolling();

      const ws = wsRef.current;
      if (ws) {
        ws.onopen = null;
        ws.onmessage = null;
        ws.onclose = null;
        ws.onerror = null;

        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        } else if (ws.readyState === WebSocket.CONNECTING) {
          // Gracefully close once the handshake finishes to avoid "closed before connection established" warning
          ws.onopen = () => {
            try { ws.close(); } catch { /* ignore */ }
          };
        }
        wsRef.current = null;
      }
    };
  }, [connect, stopPolling]);

  return { status };
}
