"""
Custom exceptions for content extraction services.
"""


class ExtractionBlockError(Exception):
    """
    Raised when content extraction is blocked by the server.
    This indicates that local extraction should be attempted instead.
    
    Examples:
    - YouTube bot detection (403 Forbidden)
    - Paywall sites requiring authentication
    - Sites blocking cloud IPs
    """
    pass