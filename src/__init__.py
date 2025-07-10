"""
Atomus TAM Research - Source Package

This package contains the core modules for the GTM Intelligence Agent.
"""

from .data_processing import AtomustamDataProcessor, CompanyData, create_data_processor
from .scoring_engine import AtomustamScoringEngine, ScoringResult, create_scoring_engine

# API integrations will be imported from subpackage
from . import api_integrations
from . import utils

__all__ = [
    # Data Processing
    'AtomustamDataProcessor',
    'CompanyData', 
    'create_data_processor',
    
    # Scoring Engine
    'AtomustamScoringEngine',
    'ScoringResult',
    'create_scoring_engine',
    
    # Subpackages
    'api_integrations',
    'utils',
]
