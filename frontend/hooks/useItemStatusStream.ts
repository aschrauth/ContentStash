import { useEffect, useRef } from 'react';
import { API_BASE_URL } from '@/lib/api';

interface UseItemStatusStreamOptions {
  onItemsUpdated?: () => void;
}

export function useItemStatusStream(options: UseItemStatusStreamOptions = {}) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectDelayRef = useRef(1000);
  const isConnectingRef = useRef(false);
  const lastActivityRef = useRef<number>(Date.now());
  const { onItemsUpdated } = options;

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) return;

    let lastPendingCount = -1;

    const connect = () => {
      // Clean up any existing connection and timeouts
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      if (eventSourceRef.current) {
        if (eventSourceRef.current.readyState !== 2) {
          eventSourceRef.current.close();
        }
        eventSourceRef.current = null;
      }

      // Guard against multiple simultaneous connection attempts
      if (isConnectingRef.current) {
        return;
      }

      isConnectingRef.current = true;
      console.log('SSE: Connecting...');
      lastActivityRef.current = Date.now();

      const eventSource = new EventSource(
        `${API_BASE_URL}/items/status-stream?token=${encodeURIComponent(token)}`
      );

      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE: Connection established');
        isConnectingRef.current = false;
        reconnectDelayRef.current = 1000; // Reset delay
        lastActivityRef.current = Date.now();
      };

      eventSource.onmessage = (event) => {
        lastActivityRef.current = Date.now();
        try {
          const data = JSON.parse(event.data);
          const currentPendingCount = data.pending_count;

          if (lastPendingCount !== -1 && lastPendingCount !== currentPendingCount) {
            if (onItemsUpdated) {
              onItemsUpdated();
            }
          }

          lastPendingCount = currentPendingCount;
        } catch (error) {
          console.error('SSE: Error parsing data:', error);
        }
      };

      eventSource.onerror = (error) => {
        // Log as warning rather than error for standard connection drops
        // especially common on mobile when backgrounding
        console.warn('SSE: Connection interrupted or failed. Attempting to reconnect...', error);

        cleanup();
        scheduleReconnect();
      };
    };

    const cleanup = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      isConnectingRef.current = false;
    };

    const scheduleReconnect = (immediate = false) => {
      if (reconnectTimeoutRef.current) return;

      const delay = immediate ? 0 : reconnectDelayRef.current;
      console.log(`SSE: Reconnecting in ${delay}ms...`);

      reconnectTimeoutRef.current = setTimeout(() => {
        reconnectTimeoutRef.current = null;
        if (!immediate) {
          reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000); // Max 30s
        }
        connect();
      }, delay);
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        const isClosed = !eventSourceRef.current || eventSourceRef.current.readyState === 2;
        const isStale = Date.now() - lastActivityRef.current > 15000; // 15s without activity

        if ((isClosed || isStale) && !isConnectingRef.current) {
          console.log('SSE: App resumed or connection stale. Reconnecting...');
          reconnectDelayRef.current = 1000;
          cleanup();
          scheduleReconnect(true);
        }
      }
    };

    const handleOnline = () => {
      const isClosed = !eventSourceRef.current || eventSourceRef.current.readyState === 2;
      if (isClosed && !isConnectingRef.current) {
        console.log('SSE: Back online. Reconnecting...');
        reconnectDelayRef.current = 1000;
        cleanup();
        scheduleReconnect(true);
      }
    };

    // Heartbeat check: Ensure we're receiving updates (backend sends every 5s)
    heartbeatCheckIntervalRef.current = setInterval(() => {
      const timeSinceLastActivity = Date.now() - lastActivityRef.current;
      // If no activity for 45 seconds, the connection might be dead even if readyState is "open"
      if (timeSinceLastActivity > 45000 && !isConnectingRef.current) {
        console.warn('SSE: Heartbeat timeout (45s). Reconnecting...');
        reconnectDelayRef.current = 1000;
        cleanup();
        scheduleReconnect(true);
      }
    }, 15000);

    // Initial connection
    connect();

    window.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('online', handleOnline);

    return () => {
      window.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('online', handleOnline);

      if (heartbeatCheckIntervalRef.current) {
        clearInterval(heartbeatCheckIntervalRef.current);
      }

      cleanup();

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [onItemsUpdated]);
}