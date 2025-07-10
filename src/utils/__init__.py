"""
Atomus TAM Research - Utilities Package

This package contains utility modules for logging, error handling, and other common functionality.
"""

from .logging_config import (
    get_logger,
    get_performance_tracker,
    get_api_logger,
    get_scoring_logger,
    log_system_info,
    log_system_shutdown
)

from .error_handling import (
    AtomustamError,
    APIError,
    ScoringError,
    DataValidationError,
    ConfigurationError,
    RetryableError,
    ErrorHandler,
    get_error_handler,
    retry_with_backoff,
    handle_api_response,
    validate_required_fields,
    safe_execute
)

__all__ = [
    # Logging
    'get_logger',
    'get_performance_tracker',
    'get_api_logger',
    'get_scoring_logger',
    'log_system_info',
    'log_system_shutdown',
    
    # Error Handling
    'AtomustamError',
    'APIError',
    'ScoringError',
    'DataValidationError',
    'ConfigurationError',
    'RetryableError',
    'ErrorHandler',
    'get_error_handler',
    'retry_with_backoff',
    'handle_api_response',
    'validate_required_fields',
    'safe_execute'
]
