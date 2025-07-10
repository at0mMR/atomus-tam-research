"""
Atomus TAM Research - API Integrations Package

This package contains API integration modules for external services.
"""

from .hubspot_client import AtomustamHubSpotClient, create_hubspot_client, HubSpotConfig
from .openai_client import AtomustamOpenAIClient, create_openai_client, OpenAIConfig
from .highergov_client import AtomustamHigherGovClient, create_highergov_client, HigherGovConfig

__all__ = [
    # HubSpot Integration
    'AtomustamHubSpotClient',
    'create_hubspot_client', 
    'HubSpotConfig',
    
    # OpenAI Integration
    'AtomustamOpenAIClient',
    'create_openai_client',
    'OpenAIConfig',
    
    # HigherGov Integration
    'AtomustamHigherGovClient',
    'create_highergov_client',
    'HigherGovConfig',
]
