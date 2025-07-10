"""
Atomus TAM Research - HigherGov API Integration
This module provides comprehensive HigherGov API integration for government contract data sourcing
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path

import requests

from ..utils import (
    get_logger,
    get_api_logger,
    get_performance_tracker,
    get_error_handler,
    APIError,
    DataValidationError,
    retry_with_backoff,
    handle_api_response,
    validate_required_fields
)


@dataclass
class HigherGovConfig:
    """Configuration for HigherGov API client"""
    api_key: str
    base_url: str = "https://api.highergov.com/v1"
    rate_limit_per_hour: int = 1000
    max_retries: int = 3
    timeout: int = 30
    default_limit: int = 100


class AtomustamHigherGovClient:
    """
    Comprehensive HigherGov API client for Atomus TAM Research
    
    This client provides:
    - Government contract data retrieval
    - Company contract history analysis
    - Defense contractor identification
    - CAGE code and DUNS number lookup
    - Contract value and duration analysis
    - Comprehensive error handling and logging
    - Integration with scoring algorithms
    """
    
    def __init__(self, config: HigherGovConfig = None):
        self.logger = get_logger("highergov_client")
        self.api_logger = get_api_logger()
        self.performance_tracker = get_performance_tracker()
        self.error_handler = get_error_handler()
        
        # Load configuration
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env()
        
        # Track API usage
        self.api_stats = {
            "total_requests": 0,
            "contracts_retrieved": 0,
            "companies_analyzed": 0,
            "errors": 0,
            "requests_by_endpoint": {},
            "rate_limit_hits": 0
        }
        
        self.logger.info(f"🏛️ HigherGov client initialized | Base URL: {self.config.base_url} | "
                        f"Rate limit: {self.config.rate_limit_per_hour}/hour")
    
    def _load_config_from_env(self) -> HigherGovConfig:
        """Load HigherGov configuration from environment variables"""
        api_key = os.getenv("HIGHERGOV_API_KEY")
        
        if not api_key:
            raise DataValidationError("HIGHERGOV_API_KEY environment variable is required")
        
        return HigherGovConfig(
            api_key=api_key,
            base_url=os.getenv("HIGHERGOV_BASE_URL", "https://api.highergov.com/v1"),
            rate_limit_per_hour=int(os.getenv("HIGHERGOV_RATE_LIMIT", "1000")),
            max_retries=int(os.getenv("HIGHERGOV_MAX_RETRIES", "3")),
            timeout=int(os.getenv("HIGHERGOV_TIMEOUT", "30")),
            default_limit=int(os.getenv("HIGHERGOV_DEFAULT_LIMIT", "100"))
        )
    
    def _handle_rate_limit(self):
        """Handle rate limiting for API calls"""
        time.sleep(3600.0 / self.config.rate_limit_per_hour)  # Space out requests evenly
    
    def _track_api_call(self, endpoint: str, success: bool = True):
        """Track API call statistics"""
        self.api_stats["total_requests"] += 1
        
        if not success:
            self.api_stats["errors"] += 1
        
        # Track by endpoint
        if endpoint not in self.api_stats["requests_by_endpoint"]:
            self.api_stats["requests_by_endpoint"][endpoint] = 0
        self.api_stats["requests_by_endpoint"][endpoint] += 1
        
        self.api_logger.log_api_call(
            "highergov",
            endpoint,
            "GET",
            success=success
        )
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make authenticated request to HigherGov API
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
        
        Returns:
            API response data
        """
        try:
            self._handle_rate_limit()
            
            url = f"{self.config.base_url}/{endpoint.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Atomus-TAM-Research/1.0"
            }
            
            response = requests.get(
                url,
                headers=headers,
                params=params or {},
                timeout=self.config.timeout
            )
            
            data = handle_api_response(response, "highergov", endpoint)
            self._track_api_call(endpoint, True)
            
            return data
            
        except Exception as e:
            self._track_api_call(endpoint, False)
            error_msg = f"HigherGov API request failed for {endpoint}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "highergov", endpoint))
            raise
    
    @retry_with_backoff(max_retries=3, backoff_factor=2.0)
    def test_connection(self) -> Dict[str, Any]:
        """
        Test HigherGov API connection
        
        Returns:
            Dictionary with connection status and API information
        """
        try:
            # Test with a simple API call
            response = self._make_request("health")
            
            self.logger.info(f"✅ HigherGov connection successful | Status: {response.get('status', 'OK')}")
            
            return {
                "status": "connected",
                "api_version": response.get("version", "unknown"),
                "rate_limit": self.config.rate_limit_per_hour,
                "connection_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_msg = f"HigherGov connection test failed: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "highergov", "health"))
            raise
    
    def search_contracts_by_company(self, company_name: str, limit: int = None,
                                  start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """
        Search for government contracts by company name
        
        Args:
            company_name: Name of the company to search for
            limit: Maximum number of contracts to return
            start_date: Start date for contract search
            end_date: End date for contract search
        
        Returns:
            List of contract data dictionaries
        """
        try:
            validate_required_fields({"company_name": company_name}, ["company_name"], "Contract search")
            
            self.performance_tracker.start_timing(f"contract_search_{company_name}")
            
            params = {
                "vendor_name": company_name,
                "limit": limit or self.config.default_limit
            }
            
            if start_date:
                params["start_date"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["end_date"] = end_date.strftime("%Y-%m-%d")
            
            self.logger.info(f"🔍 Searching contracts for: {company_name}")
            
            response = self._make_request("contracts/search", params)
            contracts = response.get("contracts", [])
            
            self.api_stats["contracts_retrieved"] += len(contracts)
            self.api_stats["companies_analyzed"] += 1
            
            self.performance_tracker.end_timing(
                f"contract_search_{company_name}",
                f"Found {len(contracts)} contracts"
            )
            
            self.logger.info(f"✅ Found {len(contracts)} contracts for {company_name}")
            
            return contracts
            
        except Exception as e:
            error_msg = f"Contract search failed for {company_name}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "highergov", "contracts/search"))
            raise
    
    def get_company_profile(self, company_name: str) -> Dict[str, Any]:
        """
        Get comprehensive company profile including contract history
        
        Args:
            company_name: Name of the company
        
        Returns:
            Company profile with contract analysis
        """
        try:
            self.logger.info(f"📋 Getting company profile: {company_name}")
            
            # Get recent contracts (last 3 years)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=3*365)
            
            contracts = self.search_contracts_by_company(
                company_name=company_name,
                start_date=start_date,
                end_date=end_date
            )
            
            # Analyze contract data
            profile = self._analyze_contract_data(company_name, contracts)
            
            self.logger.info(f"✅ Company profile completed: {company_name} | "
                           f"Contracts: {len(contracts)} | "
                           f"Defense Score: {profile.get('defense_score', 0)}")
            
            return profile
            
        except Exception as e:
            error_msg = f"Company profile failed for {company_name}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "highergov", "company_profile"))
            raise
    
    def search_defense_contracts(self, start_date: datetime = None, end_date: datetime = None,
                               min_value: float = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        Search for defense-related contracts
        
        Args:
            start_date: Start date for search
            end_date: End date for search
            min_value: Minimum contract value
            limit: Maximum number of results
        
        Returns:
            List of defense contracts
        """
        try:
            self.logger.info("🛡️ Searching for defense contracts")
            
            params = {
                "agency": "Department of Defense",
                "limit": limit or self.config.default_limit
            }
            
            if start_date:
                params["start_date"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["end_date"] = end_date.strftime("%Y-%m-%d")
            if min_value:
                params["min_value"] = min_value
            
            response = self._make_request("contracts/search", params)
            contracts = response.get("contracts", [])
            
            self.logger.info(f"✅ Found {len(contracts)} defense contracts")
            
            return contracts
            
        except Exception as e:
            error_msg = f"Defense contract search failed: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "highergov", "defense_contracts"))
            raise
    
    def get_contract_details(self, contract_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific contract
        
        Args:
            contract_id: Contract identifier
        
        Returns:
            Detailed contract information
        """
        try:
            self.logger.info(f"📄 Getting contract details: {contract_id}")
            
            response = self._make_request(f"contracts/{contract_id}")
            
            self.logger.info(f"✅ Contract details retrieved: {contract_id}")
            
            return response
            
        except Exception as e:
            error_msg = f"Contract details failed for {contract_id}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "highergov", f"contracts/{contract_id}"))
            raise
    
    def lookup_company_identifiers(self, company_name: str) -> Dict[str, Any]:
        """
        Lookup company identifiers (CAGE, DUNS, etc.)
        
        Args:
            company_name: Name of the company
        
        Returns:
            Company identifier information
        """
        try:
            self.logger.info(f"🏷️ Looking up identifiers: {company_name}")
            
            params = {"company_name": company_name}
            response = self._make_request("vendors/lookup", params)
            
            identifiers = {
                "cage_code": response.get("cage_code"),
                "duns_number": response.get("duns_number"),
                "sam_id": response.get("sam_id"),
                "ein": response.get("ein"),
                "company_name": response.get("legal_name", company_name)
            }
            
            self.logger.info(f"✅ Identifiers found: {company_name} | "
                           f"CAGE: {identifiers.get('cage_code', 'N/A')}")
            
            return identifiers
            
        except Exception as e:
            error_msg = f"Identifier lookup failed for {company_name}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "highergov", "vendors/lookup"))
            # Return empty identifiers instead of failing
            return {
                "cage_code": None,
                "duns_number": None,
                "sam_id": None,
                "ein": None,
                "company_name": company_name
            }
    
    def analyze_defense_contractor_status(self, company_name: str) -> Dict[str, Any]:
        """
        Analyze company's defense contractor status and scoring factors
        
        Args:
            company_name: Name of the company to analyze
        
        Returns:
            Defense contractor analysis with scoring data
        """
        try:
            self.performance_tracker.start_timing(f"defense_analysis_{company_name}")
            
            self.logger.info(f"🎯 Analyzing defense contractor status: {company_name}")
            
            # Get company profile with contracts
            profile = self.get_company_profile(company_name)
            
            # Get company identifiers
            identifiers = self.lookup_company_identifiers(company_name)
            
            # Combine analysis
            analysis = {
                "company_name": company_name,
                "defense_contractor_score": profile.get("defense_score", 0),
                "contract_analysis": profile.get("contract_analysis", {}),
                "identifiers": identifiers,
                "analysis_date": datetime.now().isoformat(),
                "scoring_factors": self._extract_scoring_factors(profile, identifiers)
            }
            
            self.performance_tracker.end_timing(
                f"defense_analysis_{company_name}",
                f"Score: {analysis['defense_contractor_score']}"
            )
            
            self.logger.info(f"✅ Defense analysis completed: {company_name} | "
                           f"Score: {analysis['defense_contractor_score']}")
            
            return analysis
            
        except Exception as e:
            error_msg = f"Defense contractor analysis failed for {company_name}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "highergov", "defense_analysis"))
            raise
    
    def batch_analyze_companies(self, companies: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze multiple companies for defense contractor status
        
        Args:
            companies: List of company names to analyze
        
        Returns:
            List of analysis results
        """
        self.logger.info(f"🚀 Starting batch defense contractor analysis | Companies: {len(companies)}")
        
        self.performance_tracker.start_timing("batch_defense_analysis")
        
        results = []
        failed_companies = []
        
        for i, company in enumerate(companies, 1):
            try:
                self.logger.info(f"📋 Analyzing company {i}/{len(companies)}: {company}")
                
                analysis = self.analyze_defense_contractor_status(company)
                results.append(analysis)
                
            except Exception as e:
                self.logger.error(f"❌ Failed to analyze {company}: {str(e)}")
                failed_companies.append(company)
                continue
        
        self.performance_tracker.end_timing(
            "batch_defense_analysis",
            f"Completed: {len(results)}/{len(companies)} | Failed: {len(failed_companies)}"
        )
        
        if failed_companies:
            self.logger.warning(f"⚠️ Failed to analyze {len(failed_companies)} companies: {failed_companies}")
        
        return results
    
    # UTILITY METHODS
    
    def _analyze_contract_data(self, company_name: str, contracts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze contract data to generate company profile"""
        if not contracts:
            return {
                "company_name": company_name,
                "total_contracts": 0,
                "defense_score": 0,
                "contract_analysis": {
                    "total_value": 0,
                    "defense_contracts": 0,
                    "recent_activity": False
                }
            }
        
        # Analyze contracts
        total_value = 0
        defense_contracts = 0
        defense_agencies = ["Department of Defense", "DOD", "Navy", "Army", "Air Force", "Space Force"]
        recent_cutoff = datetime.now() - timedelta(days=365)
        recent_activity = False
        
        for contract in contracts:
            # Contract value
            value = contract.get("value", 0)
            if isinstance(value, str):
                try:
                    value = float(value.replace("$", "").replace(",", ""))
                except:
                    value = 0
            total_value += value
            
            # Defense contract check
            agency = contract.get("agency", "").upper()
            if any(defense_agency.upper() in agency for defense_agency in defense_agencies):
                defense_contracts += 1
            
            # Recent activity check
            contract_date = contract.get("date_signed")
            if contract_date:
                try:
                    if isinstance(contract_date, str):
                        contract_date = datetime.fromisoformat(contract_date.replace("Z", "+00:00"))
                    if contract_date > recent_cutoff:
                        recent_activity = True
                except:
                    pass
        
        # Calculate defense score (0-100)
        defense_ratio = defense_contracts / len(contracts) if contracts else 0
        value_factor = min(total_value / 10000000, 1.0)  # Scale based on $10M
        recent_factor = 1.2 if recent_activity else 1.0
        
        defense_score = min((defense_ratio * 60 + value_factor * 30) * recent_factor, 100)
        
        return {
            "company_name": company_name,
            "total_contracts": len(contracts),
            "defense_score": round(defense_score, 1),
            "contract_analysis": {
                "total_value": total_value,
                "defense_contracts": defense_contracts,
                "defense_ratio": round(defense_ratio, 2),
                "recent_activity": recent_activity,
                "avg_contract_value": total_value / len(contracts) if contracts else 0
            }
        }
    
    def _extract_scoring_factors(self, profile: Dict[str, Any], identifiers: Dict[str, Any]) -> Dict[str, Any]:
        """Extract factors for integration with scoring engine"""
        contract_analysis = profile.get("contract_analysis", {})
        
        return {
            "has_cage_code": bool(identifiers.get("cage_code")),
            "has_duns_number": bool(identifiers.get("duns_number")),
            "defense_contract_count": contract_analysis.get("defense_contracts", 0),
            "total_contract_value": contract_analysis.get("total_value", 0),
            "defense_contract_ratio": contract_analysis.get("defense_ratio", 0),
            "recent_contract_activity": contract_analysis.get("recent_activity", False),
            "avg_contract_value": contract_analysis.get("avg_contract_value", 0)
        }
    
    def save_analysis_results(self, results: Union[Dict[str, Any], List[Dict[str, Any]]], 
                             filename: str = None) -> str:
        """
        Save analysis results to file
        
        Args:
            results: Analysis results to save
            filename: Optional filename override
        
        Returns:
            Path to saved file
        """
        try:
            # Ensure results directory exists
            results_dir = Path("data/research_results")
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"highergov_analysis_{timestamp}.json"
            
            filepath = results_dir / filename
            
            # Save results
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Analysis results saved: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            error_msg = f"Failed to save analysis results: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            raise
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return {
            **self.api_stats,
            "timestamp": datetime.now().isoformat(),
            "config": {
                "base_url": self.config.base_url,
                "rate_limit_per_hour": self.config.rate_limit_per_hour
            }
        }
    
    def log_stats_summary(self):
        """Log a summary of API usage statistics"""
        stats = self.get_api_stats()
        self.logger.info("📊 HIGHERGOV API STATS:")
        self.logger.info(f"   Total requests: {stats['total_requests']}")
        self.logger.info(f"   Contracts retrieved: {stats['contracts_retrieved']}")
        self.logger.info(f"   Companies analyzed: {stats['companies_analyzed']}")
        self.logger.info(f"   Rate limit hits: {stats['rate_limit_hits']}")
        self.logger.info(f"   Errors: {stats['errors']}")


def create_highergov_client(api_key: str = None, base_url: str = None) -> AtomustamHigherGovClient:
    """
    Factory function to create a HigherGov client
    
    Args:
        api_key: Optional API key override
        base_url: Optional base URL override
    
    Returns:
        Configured HigherGov client
    """
    config = None
    if api_key or base_url:
        config = HigherGovConfig(
            api_key=api_key or os.getenv("HIGHERGOV_API_KEY"),
            base_url=base_url or "https://api.highergov.com/v1"
        )
    
    return AtomustamHigherGovClient(config)


if __name__ == "__main__":
    # Test the HigherGov client
    from ..utils import log_system_info, log_system_shutdown
    
    log_system_info()
    
    try:
        # Create client and test connection
        client = create_highergov_client()
        
        # Test connection
        connection_info = client.test_connection()
        print(f"Connection successful: {connection_info}")
        
        # Test contract search
        contracts = client.search_contracts_by_company("Lockheed Martin")
        print(f"Found {len(contracts)} contracts for Lockheed Martin")
        
        # Test defense contractor analysis
        analysis = client.analyze_defense_contractor_status("Firestorm")
        print(f"Defense analysis for Firestorm: Score {analysis['defense_contractor_score']}")
        
        # Test batch analysis with test companies
        test_companies = ["Firehawk", "Overland AI", "Kform"]
        batch_results = client.batch_analyze_companies(test_companies)
        print(f"Batch analysis completed for {len(batch_results)} companies")
        
        # Save results
        saved_path = client.save_analysis_results(batch_results, "test_defense_analysis.json")
        print(f"Results saved to: {saved_path}")
        
        # Log final stats
        client.log_stats_summary()
        
    except Exception as e:
        logger = get_logger()
        logger.error(f"HigherGov client test failed: {str(e)}")
        
    finally:
        log_system_shutdown()
