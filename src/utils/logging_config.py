"""
Atomus TAM Research - Logging Configuration
This module sets up centralized logging for the entire application
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import colorama
from colorama import Fore, Style, Back

# Initialize colorama for colored terminal output
colorama.init()


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages in the terminal"""
    
    # Color mapping for different log levels
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Back.YELLOW
    }
    
    def format(self, record):
        # Get the original formatted message
        message = super().format(record)
        
        # Add colors if outputting to terminal
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, '')
            if color:
                message = f"{color}{message}{Style.RESET_ALL}"
        
        return message


class AtomustamLogger:
    """
    Centralized logging system for Atomus TAM Research
    
    This class provides:
    - Consistent logging across all modules
    - File and console output
    - Colored terminal output
    - Automatic log rotation
    - Performance tracking
    """
    
    def __init__(self, name: str = "atomus_tam_research"):
        self.name = name
        self.logger = None
        self._setup_directories()
        self._setup_logger()
    
    def _setup_directories(self):
        """Create necessary directories for logging"""
        self.log_dir = Path("data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different types of logs
        (self.log_dir / "api_calls").mkdir(exist_ok=True)
        (self.log_dir / "scoring").mkdir(exist_ok=True)
        (self.log_dir / "research").mkdir(exist_ok=True)
        (self.log_dir / "errors").mkdir(exist_ok=True)
        (self.log_dir / "performance").mkdir(exist_ok=True)
    
    def _setup_logger(self):
        """Set up the main logger with handlers"""
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Console handler (what you see in terminal)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self.logger.addHandler(console_handler)
        
        # Main application log file (rotating)
        main_log_file = self.log_dir / "atomus_tam_research.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
        # Error log file (only errors and critical)
        error_log_file = self.log_dir / "errors" / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(error_handler)
        
        # Performance log file
        performance_log_file = self.log_dir / "performance" / "performance.log"
        performance_handler = logging.handlers.RotatingFileHandler(
            performance_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        performance_handler.setLevel(logging.INFO)
        performance_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(performance_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance"""
        return self.logger
    
    def create_specialized_logger(self, name: str, log_file: str) -> logging.Logger:
        """
        Create a specialized logger for specific components
        
        Args:
            name: Name of the logger (e.g., 'hubspot_api', 'scoring_engine')
            log_file: Specific log file name (e.g., 'hubspot_api.log')
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(f"{self.name}.{name}")
        logger.setLevel(logging.DEBUG)
        
        # Create handler for this specific logger
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        return logger


class PerformanceTracker:
    """
    Track performance metrics and log them
    
    Use this to time operations and track system performance
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.start_times = {}
    
    def start_timing(self, operation_name: str):
        """Start timing an operation"""
        self.start_times[operation_name] = datetime.now()
        self.logger.info(f"🚀 STARTING: {operation_name}")
    
    def end_timing(self, operation_name: str, additional_info: str = ""):
        """End timing an operation and log the duration"""
        if operation_name not in self.start_times:
            self.logger.warning(f"⚠️ No start time found for operation: {operation_name}")
            return
        
        duration = datetime.now() - self.start_times[operation_name]
        duration_str = str(duration).split('.')[0]  # Remove microseconds
        
        info_str = f" | {additional_info}" if additional_info else ""
        self.logger.info(f"✅ COMPLETED: {operation_name} | Duration: {duration_str}{info_str}")
        
        # Remove from tracking
        del self.start_times[operation_name]
    
    def log_metrics(self, metrics: dict):
        """Log performance metrics"""
        metrics_str = " | ".join([f"{k}: {v}" for k, v in metrics.items()])
        self.logger.info(f"📊 METRICS: {metrics_str}")


class APICallLogger:
    """
    Specialized logger for API calls
    
    Tracks all API interactions with detailed information
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.api_call_count = {
            'hubspot': 0,
            'openai': 0,
            'highergov': 0,
            'web_scraping': 0
        }
    
    def log_api_call(self, api_name: str, endpoint: str, method: str = "GET", 
                     payload_size: int = 0, success: bool = True):
        """Log an API call with details"""
        self.api_call_count[api_name] += 1
        
        status = "✅ SUCCESS" if success else "❌ FAILED"
        self.logger.info(
            f"🔗 API CALL: {api_name.upper()} | {method} {endpoint} | "
            f"Payload: {payload_size} bytes | {status} | "
            f"Total {api_name} calls: {self.api_call_count[api_name]}"
        )
    
    def log_rate_limit(self, api_name: str, reset_time: str):
        """Log when rate limit is hit"""
        self.logger.warning(
            f"⏱️ RATE LIMIT: {api_name.upper()} | Reset time: {reset_time}"
        )
    
    def get_api_stats(self) -> dict:
        """Get API usage statistics"""
        return self.api_call_count.copy()


class ScoringLogger:
    """
    Specialized logger for scoring operations
    
    Tracks all scoring decisions and calculations
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.scoring_stats = {
            'companies_scored': 0,
            'tier_1_count': 0,
            'tier_2_count': 0,
            'tier_3_count': 0,
            'tier_4_count': 0,
            'excluded_count': 0
        }
    
    def log_company_scoring(self, company_name: str, score: float, tier: str, 
                          key_factors: list = None):
        """Log the scoring of a company"""
        self.scoring_stats['companies_scored'] += 1
        
        # Update tier counts
        tier_key = f"{tier.lower()}_count"
        if tier_key in self.scoring_stats:
            self.scoring_stats[tier_key] += 1
        
        factors_str = f" | Key factors: {', '.join(key_factors)}" if key_factors else ""
        
        self.logger.info(
            f"🎯 SCORED: {company_name} | Score: {score:.1f}/100 | "
            f"Tier: {tier} | Total scored: {self.scoring_stats['companies_scored']}{factors_str}"
        )
    
    def log_keyword_matches(self, company_name: str, keywords_found: dict):
        """Log keyword matches for a company"""
        total_keywords = sum(len(words) for words in keywords_found.values())
        
        if total_keywords > 0:
            self.logger.info(f"🔍 KEYWORDS: {company_name} | Found {total_keywords} keywords")
            for category, words in keywords_found.items():
                if words:
                    self.logger.debug(f"   {category}: {', '.join(words)}")
    
    def get_scoring_stats(self) -> dict:
        """Get scoring statistics"""
        return self.scoring_stats.copy()


# Global logger instance
_global_logger = None


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Optional name for the logger. If None, returns the main logger.
    
    Returns:
        Configured logger instance
    """
    global _global_logger
    
    if _global_logger is None:
        _global_logger = AtomustamLogger()
    
    if name:
        return _global_logger.create_specialized_logger(name, f"{name}.log")
    else:
        return _global_logger.get_logger()


def get_performance_tracker() -> PerformanceTracker:
    """Get a performance tracker instance"""
    return PerformanceTracker(get_logger())


def get_api_logger() -> APICallLogger:
    """Get an API call logger instance"""
    return APICallLogger(get_logger())


def get_scoring_logger() -> ScoringLogger:
    """Get a scoring logger instance"""
    return ScoringLogger(get_logger())


def log_system_info():
    """Log system information at startup"""
    logger = get_logger()
    
    logger.info("=" * 60)
    logger.info("🚀 ATOMUS TAM RESEARCH SYSTEM STARTING")
    logger.info("=" * 60)
    logger.info(f"📅 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🐍 Python version: {sys.version.split()[0]}")
    logger.info(f"📁 Working directory: {os.getcwd()}")
    logger.info(f"📝 Log directory: {Path('data/logs').absolute()}")
    logger.info("=" * 60)


def log_system_shutdown():
    """Log system shutdown information"""
    logger = get_logger()
    
    logger.info("=" * 60)
    logger.info("🛑 ATOMUS TAM RESEARCH SYSTEM SHUTDOWN")
    logger.info(f"📅 End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Test the logging system
    log_system_info()
    
    logger = get_logger()
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    # Test performance tracking
    tracker = get_performance_tracker()
    tracker.start_timing("test_operation")
    import time
    time.sleep(1)
    tracker.end_timing("test_operation", "Test completed successfully")
    
    # Test API logging
    api_logger = get_api_logger()
    api_logger.log_api_call("hubspot", "/companies", "GET", 1024, True)
    
    # Test scoring logging
    scoring_logger = get_scoring_logger()
    scoring_logger.log_company_scoring("Test Company", 85.5, "Tier 2", ["defense contractor", "NIST compliance"])
    
    log_system_shutdown()
