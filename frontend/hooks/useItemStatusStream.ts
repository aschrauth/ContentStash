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

    // Prevent multiple connections from being created
    if (isConnectingRef.current || eventSourceRef.current) {
      return;
    }

    let lastPendingCount = -1;

    const connect = () => {
      // Guard against multiple simultaneous connection attempts
      if (isConnectingRef.current || eventSourceRef.current) {
        return;
      }

      isConnectingRef.current = true;

      // Clean up any existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      // Create EventSource connection with token as query parameter
      const eventSource = new EventSource(
        `${API_BASE_URL}/items/status-stream?token=${encodeURIComponent(token)}`
      );

      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
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
          console.error('Error parsing SSE data:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        eventSource.close();
        eventSourceRef.current = null;
        isConnectingRef.current = false;
        
        // Exponential backoff reconnection
        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000); // Max 30s
          connect();
        }, reconnectDelayRef.current);
      };
    };

    // Initial connection
    connect();

    // Cleanup on unmount
    return () => {
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
  }, []); // Empty dependency array - only connect once per mount
}