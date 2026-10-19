import { useEffect, useRef, useState, useCallback } from 'react';
import { getWebSocketURL, alertsAPI } from '../api/client';

const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000];

/**
 * useWebSocket - manages a WebSocket connection to the backend alerts stream.
 * Falls back to HTTP polling every 8s if WebSocket fails repeatedly.
 * @param {function} onMessage - called with each parsed alert object
 */
export function useWebSocket(onMessage) {
  const wsRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef(null);
  const pollTimer = useRef(null);
  const lastAlertId = useRef(0);
  const mountedRef = useRef(true);
  const [status, setStatus] = useState('disconnected'); // 'connecting' | 'connected' | 'disconnected' | 'polling'

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
            onMessage(alert);
          }
        });
      } catch { /* ignore poll errors */ }
      if (mountedRef.current) {
        pollTimer.current = setTimeout(poll, 8000);
      }
    };
    poll();
  }, [onMessage]);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!localStorage.getItem('access_token')) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    const url = getWebSocketURL();
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      reconnectAttempts.current = 0;
      setStatus('connected');
      stopPolling();
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'NEW_ALERT') {
          onMessage(data);
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
        // Give up on WebSocket, fall back to polling
        startPolling();
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [onMessage, startPolling, stopPolling]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
      stopPolling();
    };
  }, [connect, stopPolling]);

  return { status };
}
