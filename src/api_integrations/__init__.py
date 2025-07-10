"""
Atomus TAM Research - API Integrations Package

This package contains API integration modules for external services.
"""

from .hubspot_client import AtomustamHubSpotClient, create_hubspot_client, HubSpotConfig

# Will be added in future steps
# from .openai_client import AtomustamOpenAIClient, create_openai_client
# from .highergov_client import AtomustamHigherGovClient, create_highergov_client

__all__ = [
    # HubSpot Integration
    'AtomustamHubSpotClient',
    'create_hubspot_client', 
    'HubSpotConfig',
    
    # Future integrations will be added here
]
