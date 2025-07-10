"""
Atomus TAM Research - Source Package

This package contains the core modules for the GTM Intelligence Agent.
"""

from .data_processing import AtomustamDataProcessor, CompanyData, create_data_processor

# API integrations will be imported from subpackage
from . import api_integrations
from . import utils

__all__ = [
    # Data Processing
    'AtomustamDataProcessor',
    'CompanyData', 
    'create_data_processor',
    
    # Subpackages
    'api_integrations',
    'utils',
]
