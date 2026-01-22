"""
Gemini AI Service
Provides singleton client for Google Gemini API with error handling and retries.
"""

import logging
import time
from typing import List, Optional
from functools import wraps

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from ..config import settings

logger = logging.getLogger(__name__)


class GeminiServiceError(Exception):
    """Base exception for Gemini service errors"""
    pass


class GeminiAPIKeyNotConfiguredError(GeminiServiceError):
    """Raised when Gemini API key is not configured"""
    pass


class GeminiRateLimitError(GeminiServiceError):
    """Raised when rate limit is exceeded"""
    pass


class GeminiAPIError(GeminiServiceError):
    """Raised for general Gemini API errors"""
    pass


def retry_with_exponential_backoff(max_retries: int = 1, base_delay: float = 5.0):
    """
    Decorator to retry function calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 1)
        base_delay: Base delay in seconds for exponential backoff (default: 5.0)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Configuration for rate limit handling
            rate_limit_delay = 15.0  # Wait 15 seconds for 429 errors
            max_backoff = 30.0  # Cap exponential backoff at 30 seconds
            
            for attempt in range(max_retries + 1):  # +1 to include initial attempt
                try:
                    result = func(*args, **kwargs)
                    return result
                except google_exceptions.ResourceExhausted as e:
                    
                    if attempt == max_retries:
                        logger.error(
                            f"Rate limit exceeded after {max_retries + 1} attempts. "
                            f"Please wait at least 60 seconds before retrying. Error: {str(e)}"
                        )
                        raise GeminiRateLimitError(
                            f"Rate limit exceeded. Please wait before retrying. Error: {str(e)}"
                        )
                    
                    # Use longer delay for rate limit errors to allow window to reset
                    delay = rate_limit_delay
                    logger.warning(
                        f"Rate limit hit (429 error). Waiting {delay}s to allow rate limit window to reset "
                        f"(attempt {attempt + 1}/{max_retries + 1})"
                    )
                    time.sleep(delay)
                    
                except (google_exceptions.GoogleAPIError, google_exceptions.RetryError) as e:
                    if attempt == max_retries:
                        logger.error(f"API error after {max_retries + 1} attempts: {str(e)}")
                        raise GeminiAPIError(f"API error: {str(e)}")
                    
                    # Use exponential backoff with ceiling for other API errors
                    delay = min(base_delay * (2 ** attempt), max_backoff)
                    logger.warning(
                        f"API error, retrying in {delay}s (attempt {attempt + 1}/{max_retries + 1}): {str(e)}"
                    )
                    time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                    raise GeminiAPIError(f"Unexpected error: {str(e)}")
            
            return None
        return wrapper
    return decorator


class GeminiService:
    """
    Singleton service for interacting with Google Gemini API.
    Provides text generation and embedding capabilities with error handling.
    """
    
    _instance: Optional['GeminiService'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Ensure only one instance of GeminiService exists (singleton pattern)"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the Gemini service with API key from settings"""
        if not self._initialized:
            self._configure_client()
            self._initialized = True
    
    def _configure_client(self):
        """Configure the Gemini API client with the API key"""
        if not settings.gemini_api_key:
            logger.warning("Gemini API key not configured. Service will not be available.")
            self._is_configured = False
            return
        
        try:
            genai.configure(api_key=settings.gemini_api_key)
            self._is_configured = True
            logger.info("Gemini API client configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure Gemini API client: {str(e)}")
            self._is_configured = False
            raise GeminiAPIError(f"Failed to configure Gemini client: {str(e)}")
    
    def _check_configured(self):
        """Check if the service is properly configured"""
        if not self._is_configured:
            raise GeminiAPIKeyNotConfiguredError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your environment."
            )
    
    @retry_with_exponential_backoff(max_retries=1, base_delay=5.0)
    def generate_content(
        self,
        prompt: str,
        model: str = "gemini-2.5-flash-lite"
    ) -> str:
        """
        Generate text content using Gemini API.
        
        Args:
            prompt: The input prompt for text generation
            model: The Gemini model to use (default: gemini-2.5-flash-lite)
        
        Returns:
            Generated text content as a string
        
        Raises:
            GeminiAPIKeyNotConfiguredError: If API key is not configured
            GeminiRateLimitError: If rate limit is exceeded
            GeminiAPIError: For other API errors
        """
        self._check_configured()
        
        try:
            model_instance = genai.GenerativeModel(model)
            response = model_instance.generate_content(prompt)
            
            if not response or not response.text:
                logger.warning("Empty response received from Gemini API")
                return ""
            
            logger.info(f"Successfully generated content (length: {len(response.text)} characters)")
            return response.text
            
        except google_exceptions.ResourceExhausted as e:
            # Let the retry decorator handle this
            raise
        except google_exceptions.GoogleAPIError as e:
            # Let the retry decorator handle this
            raise
        except Exception as e:
            logger.error(f"Unexpected error during content generation: {str(e)}")
            raise GeminiAPIError(f"Content generation failed: {str(e)}")
    
    @retry_with_exponential_backoff(max_retries=1, base_delay=5.0)
    def embed_content(
        self,
        text: str,
        model: str = "text-embedding-004"
    ) -> List[float]:
        """
        Generate embeddings for a single text using Gemini API.
        
        Args:
            text: The text to embed
            model: The embedding model to use (default: text-embedding-004)
        
        Returns:
            List of floats representing the embedding vector
        
        Raises:
            GeminiAPIKeyNotConfiguredError: If API key is not configured
            GeminiRateLimitError: If rate limit is exceeded
            GeminiAPIError: For other API errors
        """
        self._check_configured()
        
        try:
            result = genai.embed_content(
                model=f"models/{model}",
                content=text
            )
            
            if not result or 'embedding' not in result:
                logger.warning("No embedding returned from Gemini API")
                return []
            
            embedding = result['embedding']
            logger.info(f"Successfully generated embedding (dimension: {len(embedding)})")
            return embedding
            
        except google_exceptions.ResourceExhausted as e:
            # Let the retry decorator handle this
            raise
        except google_exceptions.GoogleAPIError as e:
            # Let the retry decorator handle this
            raise
        except Exception as e:
            logger.error(f"Unexpected error during embedding generation: {str(e)}")
            raise GeminiAPIError(f"Embedding generation failed: {str(e)}")
    
    @retry_with_exponential_backoff(max_retries=1, base_delay=5.0)
    def embed_batch(
        self,
        texts: List[str],
        model: str = "text-embedding-004"
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently using batch processing.
        
        Args:
            texts: List of texts to embed
            model: The embedding model to use (default: text-embedding-004)
        
        Returns:
            List of embedding vectors, one for each input text
        
        Raises:
            GeminiAPIKeyNotConfiguredError: If API key is not configured
            GeminiRateLimitError: If rate limit is exceeded
            GeminiAPIError: For other API errors
        """
        self._check_configured()
        
        if not texts:
            logger.warning("Empty text list provided for batch embedding")
            return []
        
        try:
            result = genai.embed_content(
                model=f"models/{model}",
                content=texts
            )
            
            if not result or 'embedding' not in result:
                logger.warning("No embeddings returned from Gemini API")
                return []
            
            # Handle both single and batch responses
            embeddings = result['embedding']
            
            # If single embedding returned, wrap in list
            if isinstance(embeddings[0], (int, float)):
                embeddings = [embeddings]
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings
            
        except google_exceptions.ResourceExhausted as e:
            # Let the retry decorator handle this
            raise
        except google_exceptions.GoogleAPIError as e:
            # Let the retry decorator handle this
            raise
        except Exception as e:
            logger.error(f"Unexpected error during batch embedding generation: {str(e)}")
            raise GeminiAPIError(f"Batch embedding generation failed: {str(e)}")
    
    def is_available(self) -> bool:
        """
        Check if the Gemini service is available and configured.
        
        Returns:
            True if service is configured and ready to use, False otherwise
        """
        return self._is_configured


# Global singleton instance
gemini_service = GeminiService()