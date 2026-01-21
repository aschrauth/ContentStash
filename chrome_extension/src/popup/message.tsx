import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './message.css';

function MessagePopup() {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Get the message from URL parameters
    const params = new URLSearchParams(window.location.search);
    const msg = params.get('message') || '';
    const loading = params.get('loading') === 'true';
    
    setMessage(msg);
    setIsLoading(loading);

    // Listen for message updates from the background script
    const messageListener = (request: any) => {
      if (request.type === 'UPDATE_MESSAGE') {
        setMessage(request.message);
        setIsLoading(request.loading || false);
        
        // If operation is complete (not loading), close after 1 second
        if (!request.loading) {
          setTimeout(() => {
            window.close();
          }, 1000);
        }
      }
    };

    chrome.runtime.onMessage.addListener(messageListener);

    return () => {
      chrome.runtime.onMessage.removeListener(messageListener);
    };
  }, []);

  return (
    <div className={`message-box ${isLoading ? 'loading' : ''}`}>
      {message}
    </div>
  );
}

const root = createRoot(document.getElementById('message-root')!);
root.render(<MessagePopup />);