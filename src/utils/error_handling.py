"""
Atomus TAM Research - Error Handling Utilities
This module provides consistent error handling across the application
"""

import functools
import traceback
import time
from typing import Any, Callable, Optional, Dict, List
from datetime import datetime
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError
import logging

from .logging_config import get_logger


class AtomustamError(Exception):
    """Base exception class for Atomus TAM Research application"""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "GENERAL_ERROR"
        self.details = details or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert error to dictionary for logging"""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class APIError(AtomustamError):
    """Exception for API-related errors"""
    
    def __init__(self, message: str, api_name: str, endpoint: str = None, 
                 status_code: int = None, response_data: dict = None):
        super().__init__(message, f"API_ERROR_{api_name.upper()}")
        self.api_name = api_name
        self.endpoint = endpoint
        self.status_code = status_code
        self.response_data = response_data or {}
        
        # Add API-specific details
        self.details.update({
            "api_name": api_name,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_data": response_data
        })


class ScoringError(AtomustamError):
    """Exception for scoring-related errors"""
    
    def __init__(self, message: str, company_name: str = None, scoring_data: dict = None):
        super().__init__(message, "SCORING_ERROR")
        self.company_name = company_name
        self.scoring_data = scoring_data or {}
        
        self.details.update({
            "company_name": company_name,
            "scoring_data": scoring_data
        })


class DataValidationError(AtomustamError):
    """Exception for data validation errors"""
    
    def __init__(self, message: str, field_name: str = None, field_value: Any = None):
        super().__init__(message, "DATA_VALIDATION_ERROR")
        self.field_name = field_name
        self.field_value = field_value
        
        self.details.update({
            "field_name": field_name,
            "field_value": str(field_value) if field_value is not None else None
        })


class ConfigurationError(AtomustamError):
    """Exception for configuration-related errors"""
    
    def __init__(self, message: str, config_key: str = None, config_file: str = None):
        super().__init__(message, "CONFIGURATION_ERROR")
        self.config_key = config_key
        self.config_file = config_file
        
        self.details.update({
            "config_key": config_key,
            "config_file": config_file
        })


class RetryableError(AtomustamError):
    """Exception for errors that can be retried"""
    
    def __init__(self, message: str, retry_count: int = 0, max_retries: int = 3):
        super().__init__(message, "RETRYABLE_ERROR")
        self.retry_count = retry_count
        self.max_retries = max_retries
        
        self.details.update({
            "retry_count": retry_count,
            "max_retries": max_retries
        })


class ErrorHandler:
    """
    Centralized error handling and reporting
    
    This class provides:
    - Consistent error logging
    - Error categorization
    - Automatic retry logic
    - Error reporting and statistics
    """
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or get_logger()
        self.error_stats = {
            "total_errors": 0,
            "api_errors": 0,
            "scoring_errors": 0,
            "validation_errors": 0,
            "configuration_errors": 0,
            "retryable_errors": 0,
            "errors_by_api": {},
            "recent_errors": []
        }
    
    def handle_error(self, error: Exception, context: str = None, 
                    critical: bool = False) -> dict:
        """
        Handle an error with consistent logging and tracking
        
        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred
            critical: Whether this error should be treated as critical
        
        Returns:
            Dictionary with error details
        """
        self.error_stats["total_errors"] += 1
        
        # Create error details
        error_details = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc()
        }
        
        # Handle specific error types
        if isinstance(error, AtomustamError):
            error_details.update(error.to_dict())
            self._update_error_stats(error)
        
        # Log the error
        log_level = logging.CRITICAL if critical else logging.ERROR
        log_message = f"❌ ERROR: {error_details['error_type']} | {error_details['message']}"
        
        if context:
            log_message += f" | Context: {context}"
        
        self.logger.log(log_level, log_message)
        self.logger.debug(f"Error details: {error_details}")
        
        # Store recent errors (keep last 100)
        self.error_stats["recent_errors"].append(error_details)
        if len(self.error_stats["recent_errors"]) > 100:
            self.error_stats["recent_errors"] = self.error_stats["recent_errors"][-100:]
        
        return error_details
    
    def _update_error_stats(self, error: AtomustamError):
        """Update error statistics based on error type"""
        if isinstance(error, APIError):
            self.error_stats["api_errors"] += 1
            api_name = error.api_name
            if api_name not in self.error_stats["errors_by_api"]:
                self.error_stats["errors_by_api"][api_name] = 0
            self.error_stats["errors_by_api"][api_name] += 1
        
        elif isinstance(error, ScoringError):
            self.error_stats["scoring_errors"] += 1
        
        elif isinstance(error, DataValidationError):
            self.error_stats["validation_errors"] += 1
        
        elif isinstance(error, ConfigurationError):
            self.error_stats["configuration_errors"] += 1
        
        elif isinstance(error, RetryableError):
            self.error_stats["retryable_errors"] += 1
    
    def get_error_stats(self) -> dict:
        """Get current error statistics"""
        return self.error_stats.copy()
    
    def get_recent_errors(self, count: int = 10) -> List[dict]:
        """Get recent errors"""
        return self.error_stats["recent_errors"][-count:]


def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 1.0, 
                      retry_exceptions: tuple = (Exception,)):
    """
    Decorator to retry functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Factor for exponential backoff (seconds)
        retry_exceptions: Tuple of exceptions that should trigger retry
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger()
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                
                except retry_exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Final attempt failed
                        logger.error(f"🔄 RETRY FAILED: {func.__name__} | "
                                   f"All {max_retries} retries exhausted | "
                                   f"Error: {str(e)}")
                        raise RetryableError(
                            f"Function {func.__name__} failed after {max_retries} retries: {str(e)}",
                            retry_count=attempt,
                            max_retries=max_retries
                        )
                    
                    # Calculate delay for exponential backoff
                    delay = backoff_factor * (2 ** attempt)
                    
                    logger.warning(f"🔄 RETRY: {func.__name__} | "
                                 f"Attempt {attempt + 1}/{max_retries} failed | "
                                 f"Retrying in {delay:.1f}s | "
                                 f"Error: {str(e)}")
                    
                    time.sleep(delay)
                
                except Exception as e:
                    # Non-retryable exception
                    logger.error(f"❌ NON-RETRYABLE: {func.__name__} | "
                               f"Error: {str(e)}")
                    raise
            
            # This should never be reached
            raise last_exception
        
        return wrapper
    return decorator


def handle_api_response(response: requests.Response, api_name: str, 
                       endpoint: str = None) -> dict:
    """
    Handle API response and raise appropriate exceptions
    
    Args:
        response: The requests response object
        api_name: Name of the API (e.g., 'hubspot', 'openai')
        endpoint: API endpoint that was called
    
    Returns:
        JSON response data
    
    Raises:
        APIError: If the API request failed
    """
    logger = get_logger()
    
    try:
        response.raise_for_status()
        
        # Log successful API call
        logger.debug(f"✅ API SUCCESS: {api_name} | {endpoint} | "
                    f"Status: {response.status_code} | "
                    f"Response size: {len(response.content)} bytes")
        
        return response.json()
    
    except HTTPError as e:
        error_msg = f"HTTP {response.status_code} error from {api_name}"
        
        # Try to extract error details from response
        try:
            error_data = response.json()
        except:
            error_data = {"response_text": response.text}
        
        logger.error(f"❌ API ERROR: {api_name} | {endpoint} | "
                    f"Status: {response.status_code} | "
                    f"Error: {error_msg}")
        
        raise APIError(
            error_msg,
            api_name=api_name,
            endpoint=endpoint,
            status_code=response.status_code,
            response_data=error_data
        )
    
    except ValueError as e:
        # JSON decode error
        error_msg = f"Invalid JSON response from {api_name}"
        logger.error(f"❌ JSON ERROR: {api_name} | {endpoint} | "
                    f"Error: {error_msg}")
        
        raise APIError(
            error_msg,
            api_name=api_name,
            endpoint=endpoint,
            status_code=response.status_code,
            response_data={"response_text": response.text}
        )


def validate_required_fields(data: dict, required_fields: List[str], 
                           context: str = None) -> None:
    """
    Validate that required fields are present in data
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        context: Additional context for error message
    
    Raises:
        DataValidationError: If any required field is missing
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        error_msg = f"Missing required fields: {', '.join(missing_fields)}"
        if context:
            error_msg = f"{context} - {error_msg}"
        
        raise DataValidationError(
            error_msg,
            field_name=missing_fields[0] if len(missing_fields) == 1 else None,
            field_value=None
        )


def safe_execute(func: Callable, error_context: str = None, 
                default_return: Any = None, log_errors: bool = True) -> Any:
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        error_context: Context for error logging
        default_return: Value to return if function fails
        log_errors: Whether to log errors
    
    Returns:
        Function result or default_return if function fails
    """
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger = get_logger()
            context_str = f" | Context: {error_context}" if error_context else ""
            logger.error(f"❌ SAFE EXECUTE FAILED: {func.__name__}{context_str} | "
                        f"Error: {str(e)}")
        
        return default_return


class ErrorReporter:
    """
    Generate error reports and summaries
    """
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.logger = get_logger()
    
    def generate_error_report(self) -> dict:
        """Generate comprehensive error report"""
        stats = self.error_handler.get_error_stats()
        recent_errors = self.error_handler.get_recent_errors(20)
        
        report = {
            "report_generated": datetime.now().isoformat(),
            "summary": {
                "total_errors": stats["total_errors"],
                "error_breakdown": {
                    "api_errors": stats["api_errors"],
                    "scoring_errors": stats["scoring_errors"],
                    "validation_errors": stats["validation_errors"],
                    "configuration_errors": stats["configuration_errors"],
                    "retryable_errors": stats["retryable_errors"]
                },
                "api_error_breakdown": stats["errors_by_api"]
            },
            "recent_errors": recent_errors
        }
        
        return report
    
    def log_error_summary(self):
        """Log a summary of errors"""
        stats = self.error_handler.get_error_stats()
        
        if stats["total_errors"] == 0:
            self.logger.info("✅ ERROR SUMMARY: No errors recorded")
            return
        
        self.logger.info("📊 ERROR SUMMARY:")
        self.logger.info(f"   Total errors: {stats['total_errors']}")
        self.logger.info(f"   API errors: {stats['api_errors']}")
        self.logger.info(f"   Scoring errors: {stats['scoring_errors']}")
        self.logger.info(f"   Validation errors: {stats['validation_errors']}")
        self.logger.info(f"   Configuration errors: {stats['configuration_errors']}")
        
        if stats["errors_by_api"]:
            self.logger.info("   API error breakdown:")
            for api, count in stats["errors_by_api"].items():
                self.logger.info(f"     {api}: {count} errors")


# Global error handler instance
_global_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _global_error_handler
    
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    
    return _global_error_handler


if __name__ == "__main__":
    # Test the error handling system
    logger = get_logger()
    error_handler = get_error_handler()
    
    # Test different error types
    try:
        raise APIError("Test API error", "hubspot", "/companies", 401, {"error": "unauthorized"})
    except APIError as e:
        error_handler.handle_error(e, "Testing API error handling")
    
    try:
        raise ScoringError("Test scoring error", "Test Company", {"score": 0})
    except ScoringError as e:
        error_handler.handle_error(e, "Testing scoring error handling")
    
    try:
        raise DataValidationError("Test validation error", "company_name", None)
    except DataValidationError as e:
        error_handler.handle_error(e, "Testing validation error handling")
    
    # Test retry decorator
    @retry_with_backoff(max_retries=2, backoff_factor=0.1)
    def failing_function():
        raise ConnectionError("Test connection error")
    
    try:
        failing_function()
    except RetryableError as e:
        error_handler.handle_error(e, "Testing retry functionality")
    
    # Generate error report
    reporter = ErrorReporter(error_handler)
    reporter.log_error_summary()
    
    logger.info("Error handling system test completed")
