import { useEffect, useRef } from 'react';
import { API_BASE_URL } from '@/lib/api';

interface UseItemStatusStreamOptions {
  onItemsUpdated?: () => void;
}

export function useItemStatusStream(options: UseItemStatusStreamOptions = {}) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectDelayRef = useRef(1000); // Start with 1 second
  const isConnectingRef = useRef(false); // Guard to prevent multiple simultaneous connections
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
        // Only close if it's not already closed
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

      // Create EventSource connection with token as query parameter
      const eventSource = new EventSource(
        `${API_BASE_URL}/items/status-stream?token=${encodeURIComponent(token)}`
      );

      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE: Connection established');
        isConnectingRef.current = false;
        // Reset delay on successful connection
        reconnectDelayRef.current = 1000;
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const currentPendingCount = data.pending_count;

          // If pending count changed (increased or decreased), refresh items
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
        console.error('SSE: Connection error', error);

        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }

        isConnectingRef.current = false;

        // Exponential backoff reconnection
        if (!reconnectTimeoutRef.current) {
          console.log(`SSE: Reconnecting in ${reconnectDelayRef.current}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000); // Max 30s
            connect();
          }, reconnectDelayRef.current);
        }
      };
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        const isClosed = !eventSourceRef.current || eventSourceRef.current.readyState === 2;
        if (isClosed && !isConnectingRef.current) {
          console.log('SSE: Page visible, connection lost. Reconnecting...');
          reconnectDelayRef.current = 1000; // Reset delay for immediate reconnection
          connect();
        }
      }
    };

    const handleOnline = () => {
      const isClosed = !eventSourceRef.current || eventSourceRef.current.readyState === 2;
      if (isClosed && !isConnectingRef.current) {
        console.log('SSE: Back online. Reconnecting...');
        reconnectDelayRef.current = 1000; // Reset delay
        connect();
      }
    };

    // Initial connection
    connect();

    // Listen for visibility and online events
    window.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('online', handleOnline);

    // Cleanup on unmount
    return () => {
      window.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('online', handleOnline);

      isConnectingRef.current = false;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };
  }, [onItemsUpdated]); // Re-run if handler changes
}