"""
Atomus TAM Research - HubSpot API Integration
This module provides comprehensive HubSpot API integration for CRM operations
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

import requests
from hubspot import HubSpot
from hubspot.crm.companies import ApiException as CompaniesApiException
from hubspot.crm.contacts import ApiException as ContactsApiException
from hubspot.crm.properties import ApiException as PropertiesApiException

from ..utils import (
    get_logger, 
    get_api_logger, 
    get_error_handler,
    APIError, 
    DataValidationError,
    retry_with_backoff,
    handle_api_response,
    validate_required_fields
)


@dataclass
class HubSpotConfig:
    """Configuration for HubSpot API client"""
    api_key: str
    portal_id: Optional[str] = None
    rate_limit_per_second: int = 10
    batch_size: int = 100
    max_retries: int = 3
    base_url: str = "https://api.hubapi.com"


class AtomustamHubSpotClient:
    """
    Comprehensive HubSpot API client for Atomus TAM Research
    
    This client provides:
    - Company management and custom properties
    - Contact enrichment and management  
    - Deal and pipeline management
    - Custom property creation and management
    - Bulk operations with rate limiting
    - Comprehensive error handling and logging
    """
    
    def __init__(self, config: HubSpotConfig = None):
        self.logger = get_logger("hubspot_client")
        self.api_logger = get_api_logger()
        self.error_handler = get_error_handler()
        
        # Load configuration
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env()
        
        # Initialize HubSpot client
        self.client = HubSpot(api_key=self.config.api_key)
        
        # Track API usage
        self.api_stats = {
            "total_calls": 0,
            "companies_created": 0,
            "companies_updated": 0,
            "contacts_created": 0,
            "contacts_updated": 0,
            "properties_created": 0,
            "rate_limit_hits": 0,
            "errors": 0
        }
        
        self.logger.info(f"🔗 HubSpot client initialized | Rate limit: {self.config.rate_limit_per_second}/sec")
    
    def _load_config_from_env(self) -> HubSpotConfig:
        """Load HubSpot configuration from environment variables"""
        api_key = os.getenv("HUBSPOT_API_KEY", "na2-c562-6153-4837-bf92-c9abc4cc7ef7")
        portal_id = os.getenv("HUBSPOT_PORTAL_ID")
        
        if not api_key:
            raise DataValidationError("HUBSPOT_API_KEY environment variable is required")
        
        return HubSpotConfig(
            api_key=api_key,
            portal_id=portal_id,
            rate_limit_per_second=int(os.getenv("HUBSPOT_RATE_LIMIT", "10")),
            batch_size=int(os.getenv("HUBSPOT_BATCH_SIZE", "100")),
            max_retries=int(os.getenv("HUBSPOT_MAX_RETRIES", "3"))
        )
    
    def _handle_rate_limit(self):
        """Handle rate limiting for API calls"""
        time.sleep(1.0 / self.config.rate_limit_per_second)
    
    def _track_api_call(self, operation: str, success: bool = True):
        """Track API call statistics"""
        self.api_stats["total_calls"] += 1
        if not success:
            self.api_stats["errors"] += 1
        
        self.api_logger.log_api_call(
            "hubspot", 
            operation, 
            "POST" if operation in ["create", "update"] else "GET",
            success=success
        )
    
    @retry_with_backoff(max_retries=3, backoff_factor=1.0)
    def test_connection(self) -> Dict[str, Any]:
        """
        Test HubSpot API connection and return account info
        
        Returns:
            Dictionary with account information and connection status
        """
        try:
            self._handle_rate_limit()
            
            # Get account info to test connection
            response = requests.get(
                f"{self.config.base_url}/account-info/v3/details",
                headers={"authorization": f"Bearer {self.config.api_key}"}
            )
            
            account_info = handle_api_response(response, "hubspot", "/account-info/v3/details")
            
            self._track_api_call("test_connection", True)
            self.logger.info(f"✅ HubSpot connection successful | Portal: {account_info.get('portalId')}")
            
            return {
                "status": "connected",
                "portal_id": account_info.get("portalId"),
                "account_type": account_info.get("accountType"),
                "currency": account_info.get("currency"),
                "time_zone": account_info.get("timeZone"),
                "connection_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self._track_api_call("test_connection", False)
            error_msg = f"HubSpot connection test failed: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "hubspot", "/account-info"))
            raise
    
    # COMPANY MANAGEMENT
    
    def get_company(self, company_id: str, properties: List[str] = None) -> Dict[str, Any]:
        """
        Get a company by ID with specified properties
        
        Args:
            company_id: HubSpot company ID
            properties: List of properties to retrieve
        
        Returns:
            Company data dictionary
        """
        try:
            self._handle_rate_limit()
            
            if properties is None:
                properties = ["name", "domain", "industry", "country", "state", "city", 
                            "numberofemployees", "annualrevenue", "website"]
            
            company = self.client.crm.companies.basic_api.get_by_id(
                company_id=company_id,
                properties=properties
            )
            
            self._track_api_call(f"get_company/{company_id}", True)
            self.logger.debug(f"📋 Retrieved company: {company.properties.get('name', 'Unknown')}")
            
            return self._format_company_data(company)
            
        except CompaniesApiException as e:
            self._track_api_call(f"get_company/{company_id}", False)
            error_msg = f"Failed to get company {company_id}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "hubspot", f"/companies/{company_id}"))
            raise
    
    def search_companies(self, filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for companies using filters
        
        Args:
            filters: Search filters (e.g., {"name": "Acme Corp", "industry": "Technology"})
            limit: Maximum number of results
        
        Returns:
            List of company data dictionaries
        """
        try:
            self._handle_rate_limit()
            
            # Build search request
            filter_groups = []
            for property_name, value in filters.items():
                filter_groups.append({
                    "filters": [{
                        "propertyName": property_name,
                        "operator": "CONTAINS_TOKEN" if isinstance(value, str) else "EQ",
                        "value": value
                    }]
                })
            
            search_request = {
                "filterGroups": filter_groups,
                "limit": min(limit, 100),
                "properties": ["name", "domain", "industry", "country", "numberofemployees", "annualrevenue"]
            }
            
            results = self.client.crm.companies.search_api.do_search(
                public_object_search_request=search_request
            )
            
            companies = [self._format_company_data(company) for company in results.results]
            
            self._track_api_call("search_companies", True)
            self.logger.info(f"🔍 Found {len(companies)} companies matching search criteria")
            
            return companies
            
        except CompaniesApiException as e:
            self._track_api_call("search_companies", False)
            error_msg = f"Company search failed: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "hubspot", "/companies/search"))
            raise
    
    def create_company(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new company in HubSpot
        
        Args:
            company_data: Company properties dictionary
        
        Returns:
            Created company data
        """
        try:
            validate_required_fields(company_data, ["name"], "Company creation")
            
            self._handle_rate_limit()
            
            # Create company
            company = self.client.crm.companies.basic_api.create(
                simple_public_object_input={"properties": company_data}
            )
            
            self.api_stats["companies_created"] += 1
            self._track_api_call("create_company", True)
            
            company_name = company_data.get("name", "Unknown")
            self.logger.info(f"✅ Created company: {company_name} | ID: {company.id}")
            
            return self._format_company_data(company)
            
        except CompaniesApiException as e:
            self._track_api_call("create_company", False)
            error_msg = f"Failed to create company: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "hubspot", "/companies"))
            raise
    
    def update_company(self, company_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing company
        
        Args:
            company_id: HubSpot company ID
            updates: Properties to update
        
        Returns:
            Updated company data
        """
        try:
            self._handle_rate_limit()
            
            company = self.client.crm.companies.basic_api.update(
                company_id=company_id,
                simple_public_object_input={"properties": updates}
            )
            
            self.api_stats["companies_updated"] += 1
            self._track_api_call(f"update_company/{company_id}", True)
            
            self.logger.info(f"✅ Updated company ID: {company_id} | Properties: {list(updates.keys())}")
            
            return self._format_company_data(company)
            
        except CompaniesApiException as e:
            self._track_api_call(f"update_company/{company_id}", False)
            error_msg = f"Failed to update company {company_id}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "hubspot", f"/companies/{company_id}"))
            raise
    
    # CUSTOM PROPERTIES MANAGEMENT
    
    def create_custom_property(self, object_type: str, property_definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a custom property for companies or contacts
        
        Args:
            object_type: "companies" or "contacts"
            property_definition: Property configuration
        
        Returns:
            Created property information
        """
        try:
            validate_required_fields(property_definition, ["name", "label", "type"], "Property creation")
            
            self._handle_rate_limit()
            
            # Create the property
            property_create_request = {
                "name": property_definition["name"],
                "label": property_definition["label"],
                "type": property_definition["type"],
                "fieldType": property_definition.get("fieldType", "text"),
                "groupName": property_definition.get("groupName", "atomus_tam_research"),
                "description": property_definition.get("description", ""),
                "options": property_definition.get("options", [])
            }
            
            if object_type == "companies":
                response = self.client.crm.properties.core_api.create(
                    object_type="companies",
                    property_create=property_create_request
                )
            elif object_type == "contacts":
                response = self.client.crm.properties.core_api.create(
                    object_type="contacts", 
                    property_create=property_create_request
                )
            else:
                raise DataValidationError(f"Invalid object_type: {object_type}. Must be 'companies' or 'contacts'")
            
            self.api_stats["properties_created"] += 1
            self._track_api_call(f"create_property/{object_type}", True)
            
            self.logger.info(f"✅ Created custom property: {property_definition['name']} for {object_type}")
            
            return {
                "name": response.name,
                "label": response.label,
                "type": response.type,
                "field_type": response.field_type,
                "created_at": response.created_at
            }
            
        except PropertiesApiException as e:
            self._track_api_call(f"create_property/{object_type}", False)
            error_msg = f"Failed to create custom property: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "hubspot", f"/properties/{object_type}"))
            raise
    
    def setup_atomus_properties(self) -> Dict[str, List[str]]:
        """
        Set up all custom properties needed for Atomus TAM Research
        
        Returns:
            Dictionary with created properties by object type
        """
        self.logger.info("🏗️ Setting up Atomus custom properties in HubSpot...")
        
        created_properties = {"companies": [], "contacts": []}
        
        # Company properties for scoring and research
        company_properties = [
            {
                "name": "atomus_score",
                "label": "Atomus Score", 
                "type": "number",
                "fieldType": "number",
                "description": "Overall Atomus TAM score (0-100)"
            },
            {
                "name": "defense_contract_score",
                "label": "Defense Contract Score",
                "type": "number", 
                "fieldType": "number",
                "description": "Score based on defense contracting history and likelihood"
            },
            {
                "name": "technology_relevance_score",
                "label": "Technology Relevance Score",
                "type": "number",
                "fieldType": "number", 
                "description": "Score based on technology stack relevance to NIST/CMMC"
            },
            {
                "name": "compliance_indicators_score",
                "label": "Compliance Indicators Score",
                "type": "number",
                "fieldType": "number",
                "description": "Score based on existing compliance posture"
            },
            {
                "name": "tier_classification",
                "label": "Tier Classification",
                "type": "enumeration",
                "fieldType": "select",
                "description": "Atomus tier classification based on score",
                "options": [
                    {"label": "Tier 1 (90-100)", "value": "tier_1"},
                    {"label": "Tier 2 (75-89)", "value": "tier_2"},
                    {"label": "Tier 3 (60-74)", "value": "tier_3"},
                    {"label": "Tier 4 (45-59)", "value": "tier_4"},
                    {"label": "Excluded (<45)", "value": "excluded"}
                ]
            },
            {
                "name": "last_research_date",
                "label": "Last Research Date",
                "type": "datetime",
                "fieldType": "date",
                "description": "Date of last research conducted"
            },
            {
                "name": "next_review_date", 
                "label": "Next Review Date",
                "type": "datetime",
                "fieldType": "date",
                "description": "Scheduled date for next review"
            },
            {
                "name": "research_summary",
                "label": "Research Summary",
                "type": "string",
                "fieldType": "textarea",
                "description": "Summary of research findings"
            },
            {
                "name": "contract_history",
                "label": "Contract History",
                "type": "string",
                "fieldType": "textarea",
                "description": "Government contract history and details"
            },
            {
                "name": "technology_keywords_found",
                "label": "Technology Keywords Found",
                "type": "string", 
                "fieldType": "textarea",
                "description": "Keywords found during research that indicate technology relevance"
            }
        ]
        
        # Contact properties for persona and validation
        contact_properties = [
            {
                "name": "persona_type",
                "label": "Persona Type",
                "type": "enumeration",
                "fieldType": "select",
                "description": "Contact persona classification",
                "options": [
                    {"label": "CISO", "value": "ciso"},
                    {"label": "IT Director", "value": "it_director"},
                    {"label": "Compliance Officer", "value": "compliance_officer"},
                    {"label": "CTO", "value": "cto"},
                    {"label": "Security Manager", "value": "security_manager"},
                    {"label": "Other", "value": "other"}
                ]
            },
            {
                "name": "validation_status",
                "label": "Validation Status",
                "type": "enumeration",
                "fieldType": "select", 
                "description": "Contact validation status",
                "options": [
                    {"label": "Validated", "value": "validated"},
                    {"label": "Pending", "value": "pending"},
                    {"label": "Invalid", "value": "invalid"}
                ]
            },
            {
                "name": "enrichment_source",
                "label": "Enrichment Source",
                "type": "string",
                "fieldType": "text",
                "description": "Source of contact enrichment data"
            },
            {
                "name": "contact_score",
                "label": "Contact Score",
                "type": "number",
                "fieldType": "number",
                "description": "Contact quality and relevance score"
            },
            {
                "name": "last_verified_date",
                "label": "Last Verified Date", 
                "type": "datetime",
                "fieldType": "date",
                "description": "Date contact information was last verified"
            }
        ]
        
        # Create company properties
        for prop in company_properties:
            try:
                result = self.create_custom_property("companies", prop)
                created_properties["companies"].append(prop["name"])
            except Exception as e:
                if "already exists" in str(e).lower():
                    self.logger.warning(f"⚠️ Property {prop['name']} already exists, skipping")
                else:
                    self.logger.error(f"❌ Failed to create company property {prop['name']}: {str(e)}")
        
        # Create contact properties  
        for prop in contact_properties:
            try:
                result = self.create_custom_property("contacts", prop)
                created_properties["contacts"].append(prop["name"])
            except Exception as e:
                if "already exists" in str(e).lower():
                    self.logger.warning(f"⚠️ Property {prop['name']} already exists, skipping")
                else:
                    self.logger.error(f"❌ Failed to create contact property {prop['name']}: {str(e)}")
        
        self.logger.info(f"✅ Property setup complete | "
                        f"Companies: {len(created_properties['companies'])} | "
                        f"Contacts: {len(created_properties['contacts'])}")
        
        return created_properties
    
    # UTILITY METHODS
    
    def _format_company_data(self, company) -> Dict[str, Any]:
        """Format HubSpot company object to standardized dictionary"""
        return {
            "id": company.id,
            "properties": company.properties,
            "created_at": company.created_at,
            "updated_at": company.updated_at
        }
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return {
            **self.api_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def log_stats_summary(self):
        """Log a summary of API usage statistics"""
        stats = self.get_api_stats()
        self.logger.info("📊 HUBSPOT API STATS:")
        self.logger.info(f"   Total calls: {stats['total_calls']}")
        self.logger.info(f"   Companies created: {stats['companies_created']}")
        self.logger.info(f"   Companies updated: {stats['companies_updated']}")
        self.logger.info(f"   Properties created: {stats['properties_created']}")
        self.logger.info(f"   Errors: {stats['errors']}")


def create_hubspot_client(api_key: str = None) -> AtomustamHubSpotClient:
    """
    Factory function to create a HubSpot client
    
    Args:
        api_key: Optional API key override
    
    Returns:
        Configured HubSpot client
    """
    if api_key:
        config = HubSpotConfig(api_key=api_key)
        return AtomustamHubSpotClient(config)
    else:
        return AtomustamHubSpotClient()


if __name__ == "__main__":
    # Test the HubSpot client
    from ..utils import log_system_info, log_system_shutdown
    
    log_system_info()
    
    try:
        # Create client and test connection
        client = create_hubspot_client()
        
        # Test connection
        connection_info = client.test_connection()
        print(f"Connection successful: {connection_info}")
        
        # Set up custom properties
        created_properties = client.setup_atomus_properties()
        print(f"Created properties: {created_properties}")
        
        # Log final stats
        client.log_stats_summary()
        
    except Exception as e:
        logger = get_logger()
        logger.error(f"HubSpot client test failed: {str(e)}")
        
    finally:
        log_system_shutdown()
