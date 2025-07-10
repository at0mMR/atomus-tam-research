"""
Atomus TAM Research - Data Processing Foundation
This module provides comprehensive data validation, transformation, and management capabilities
"""

import os
import re
import csv
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import yaml

from .utils import (
    get_logger,
    get_performance_tracker,
    get_error_handler,
    DataValidationError,
    validate_required_fields,
    safe_execute
)


@dataclass
class CompanyData:
    """Standardized company data structure"""
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = "United States"
    state: Optional[str] = None
    city: Optional[str] = None
    employee_count: Optional[int] = None
    annual_revenue: Optional[float] = None
    description: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    
    # Atomus-specific fields
    atomus_score: Optional[float] = None
    defense_contract_score: Optional[float] = None
    technology_relevance_score: Optional[float] = None
    compliance_indicators_score: Optional[float] = None
    tier_classification: Optional[str] = None
    
    # Research and tracking
    last_research_date: Optional[str] = None
    next_review_date: Optional[str] = None
    research_summary: Optional[str] = None
    contract_history: Optional[str] = None
    technology_keywords_found: Optional[str] = None
    
    # Identifiers
    cage_code: Optional[str] = None
    duns_number: Optional[str] = None
    hubspot_id: Optional[str] = None
    
    # Metadata
    created_date: Optional[str] = None
    updated_date: Optional[str] = None
    data_source: Optional[str] = None
    validation_status: str = "pending"


class AtomustamDataProcessor:
    """
    Comprehensive data processing system for Atomus TAM Research
    
    This processor provides:
    - Data validation and cleaning
    - Company data normalization
    - Prospect database management
    - Data transformation for scoring
    - Integration with API data
    - Data deduplication and quality checks
    """
    
    def __init__(self):
        self.logger = get_logger("data_processor")
        self.performance_tracker = get_performance_tracker()
        self.error_handler = get_error_handler()
        
        # Load validation rules
        self.validation_rules = self._load_validation_rules()
        
        # Data quality statistics
        self.stats = {
            "records_processed": 0,
            "records_validated": 0,
            "records_rejected": 0,
            "duplicates_found": 0,
            "data_quality_score": 0.0
        }
        
        self.logger.info("📊 Data processor initialized")
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load data validation rules from configuration"""
        try:
            # Try to load from config file
            config_path = Path("config/scoring_config.yaml")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get("algorithm_parameters", {}).get("validation_rules", {})
        except Exception as e:
            self.logger.warning(f"⚠️ Could not load validation rules: {str(e)}")
        
        # Return default validation rules
        return {
            "minimum_data_points": 3,
            "exclude_incomplete_profiles": False,
            "require_website": True,
            "require_industry_classification": True,
            "max_company_name_length": 100,
            "valid_countries": ["United States", "Canada"],
            "min_employee_count": 1,
            "max_employee_count": 50000
        }
    
    def validate_company_data(self, data: Union[Dict[str, Any], CompanyData]) -> Tuple[bool, List[str]]:
        """
        Validate company data against business rules
        
        Args:
            data: Company data to validate
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # Convert to dict if CompanyData object
            if isinstance(data, CompanyData):
                data_dict = asdict(data)
            else:
                data_dict = data
            
            # Required field validation
            required_fields = ["name"]
            try:
                validate_required_fields(data_dict, required_fields, "Company data validation")
            except DataValidationError as e:
                errors.append(str(e))
            
            # Company name validation
            name = data_dict.get("name", "")
            if not name or len(name.strip()) == 0:
                errors.append("Company name cannot be empty")
            elif len(name) > self.validation_rules.get("max_company_name_length", 100):
                errors.append(f"Company name too long (max {self.validation_rules.get('max_company_name_length', 100)} characters)")
            
            # Website validation
            if self.validation_rules.get("require_website", True):
                website = data_dict.get("website") or data_dict.get("domain")
                if not website:
                    errors.append("Website/domain is required")
                elif not self._validate_url(website):
                    errors.append("Invalid website URL format")
            
            # Industry validation
            if self.validation_rules.get("require_industry_classification", True):
                industry = data_dict.get("industry")
                if not industry:
                    errors.append("Industry classification is required")
            
            # Employee count validation
            employee_count = data_dict.get("employee_count")
            if employee_count is not None:
                if not isinstance(employee_count, int) or employee_count < self.validation_rules.get("min_employee_count", 1):
                    errors.append("Invalid employee count")
                elif employee_count > self.validation_rules.get("max_employee_count", 50000):
                    errors.append("Employee count exceeds maximum limit")
            
            # Revenue validation
            revenue = data_dict.get("annual_revenue")
            if revenue is not None:
                if not isinstance(revenue, (int, float)) or revenue < 0:
                    errors.append("Invalid annual revenue")
            
            # Country validation
            country = data_dict.get("country")
            valid_countries = self.validation_rules.get("valid_countries", ["United States"])
            if country and country not in valid_countries:
                errors.append(f"Country must be one of: {', '.join(valid_countries)}")
            
            # Score validation
            for score_field in ["atomus_score", "defense_contract_score", "technology_relevance_score", "compliance_indicators_score"]:
                score = data_dict.get(score_field)
                if score is not None:
                    if not isinstance(score, (int, float)) or score < 0 or score > 100:
                        errors.append(f"Invalid {score_field}: must be between 0 and 100")
            
            # Tier validation
            tier = data_dict.get("tier_classification")
            if tier and tier not in ["tier_1", "tier_2", "tier_3", "tier_4", "excluded"]:
                errors.append("Invalid tier classification")
            
            # Data completeness check
            data_points = sum(1 for value in data_dict.values() if value is not None and value != "")
            min_data_points = self.validation_rules.get("minimum_data_points", 3)
            if data_points < min_data_points:
                if self.validation_rules.get("exclude_incomplete_profiles", False):
                    errors.append(f"Insufficient data points: {data_points} < {min_data_points}")
                else:
                    self.logger.warning(f"⚠️ Low data quality for {name}: {data_points} data points")
            
            is_valid = len(errors) == 0
            
            if is_valid:
                self.stats["records_validated"] += 1
            else:
                self.stats["records_rejected"] += 1
                self.logger.warning(f"⚠️ Validation failed for {name}: {'; '.join(errors)}")
            
            self.stats["records_processed"] += 1
            
            return is_valid, errors
            
        except Exception as e:
            error_msg = f"Validation error for company data: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            return False, [error_msg]
    
    def clean_and_normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize company data
        
        Args:
            data: Raw company data
        
        Returns:
            Cleaned and normalized data
        """
        try:
            cleaned_data = {}
            
            # Clean company name
            name = data.get("name", "").strip()
            if name:
                # Remove common company suffixes for normalization
                name = re.sub(r'\s+(Inc\.?|LLC|Corp\.?|Corporation|Ltd\.?|Limited)\s*$', '', name, flags=re.IGNORECASE)
                cleaned_data["name"] = name.strip()
            
            # Normalize website/domain
            website = data.get("website") or data.get("domain", "")
            if website:
                website = self._normalize_url(website)
                cleaned_data["website"] = website
                cleaned_data["domain"] = self._extract_domain(website)
            
            # Clean and normalize text fields
            text_fields = ["industry", "description", "research_summary", "contract_history"]
            for field in text_fields:
                value = data.get(field)
                if value:
                    # Clean whitespace and normalize
                    cleaned_value = re.sub(r'\s+', ' ', str(value)).strip()
                    cleaned_data[field] = cleaned_value
            
            # Normalize location data
            if data.get("country"):
                cleaned_data["country"] = data["country"].strip().title()
            if data.get("state"):
                cleaned_data["state"] = data["state"].strip().upper()
            if data.get("city"):
                cleaned_data["city"] = data["city"].strip().title()
            
            # Normalize numeric fields
            numeric_fields = ["employee_count", "annual_revenue", "atomus_score", "defense_contract_score", 
                            "technology_relevance_score", "compliance_indicators_score"]
            for field in numeric_fields:
                value = data.get(field)
                if value is not None:
                    try:
                        # Handle string numbers
                        if isinstance(value, str):
                            value = value.replace(",", "").replace("$", "")
                        cleaned_data[field] = float(value) if field != "employee_count" else int(float(value))
                    except (ValueError, TypeError):
                        self.logger.warning(f"⚠️ Could not normalize {field}: {value}")
            
            # Normalize identifiers
            if data.get("cage_code"):
                cleaned_data["cage_code"] = str(data["cage_code"]).strip().upper()
            if data.get("duns_number"):
                cleaned_data["duns_number"] = str(data["duns_number"]).strip()
            
            # Add metadata
            cleaned_data["updated_date"] = datetime.now().isoformat()
            if not data.get("created_date"):
                cleaned_data["created_date"] = datetime.now().isoformat()
            
            # Copy other fields as-is
            for key, value in data.items():
                if key not in cleaned_data and value is not None:
                    cleaned_data[key] = value
            
            self.logger.debug(f"📝 Cleaned data for: {cleaned_data.get('name', 'Unknown')}")
            
            return cleaned_data
            
        except Exception as e:
            error_msg = f"Data cleaning failed: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            return data  # Return original data if cleaning fails
    
    def deduplicate_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate companies based on multiple criteria
        
        Args:
            companies: List of company dictionaries
        
        Returns:
            Deduplicated list of companies
        """
        try:
            self.logger.info(f"🔍 Deduplicating {len(companies)} companies")
            
            seen_companies = {}
            duplicates_found = 0
            
            for company in companies:
                # Create deduplication keys
                name_key = self._normalize_company_name(company.get("name", ""))
                domain_key = self._extract_domain(company.get("website") or company.get("domain", ""))
                
                # Check for duplicates
                duplicate_found = False
                
                # Check by normalized name
                if name_key in seen_companies:
                    duplicate_found = True
                    self.logger.debug(f"🔄 Duplicate by name: {company.get('name')}")
                
                # Check by domain
                elif domain_key and any(self._extract_domain(existing.get("website", "")) == domain_key 
                                      for existing in seen_companies.values()):
                    duplicate_found = True
                    self.logger.debug(f"🔄 Duplicate by domain: {domain_key}")
                
                if duplicate_found:
                    duplicates_found += 1
                    # Merge data from duplicate (keep most complete record)
                    existing_key = name_key if name_key in seen_companies else next(
                        key for key, existing in seen_companies.items() 
                        if self._extract_domain(existing.get("website", "")) == domain_key
                    )
                    seen_companies[existing_key] = self._merge_company_data(
                        seen_companies[existing_key], company
                    )
                else:
                    seen_companies[name_key] = company
            
            deduplicated = list(seen_companies.values())
            
            self.stats["duplicates_found"] += duplicates_found
            
            self.logger.info(f"✅ Deduplication complete | Original: {len(companies)} | "
                           f"Final: {len(deduplicated)} | Duplicates removed: {duplicates_found}")
            
            return deduplicated
            
        except Exception as e:
            error_msg = f"Deduplication failed: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            return companies  # Return original list if deduplication fails
    
    def load_prospect_database(self, file_path: str = None) -> pd.DataFrame:
        """
        Load the prospect database from CSV file
        
        Args:
            file_path: Optional path to CSV file
        
        Returns:
            DataFrame with prospect data
        """
        try:
            if not file_path:
                file_path = "data/prospect_database.csv"
            
            file_path = Path(file_path)
            
            if not file_path.exists():
                self.logger.warning(f"⚠️ Prospect database not found: {file_path}")
                return pd.DataFrame()
            
            self.logger.info(f"📖 Loading prospect database: {file_path}")
            
            df = pd.read_csv(file_path)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
            
            self.logger.info(f"✅ Loaded {len(df)} companies from prospect database")
            
            return df
            
        except Exception as e:
            error_msg = f"Failed to load prospect database: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            return pd.DataFrame()
    
    def save_prospect_database(self, df: pd.DataFrame, file_path: str = None) -> str:
        """
        Save the prospect database to CSV file
        
        Args:
            df: DataFrame with prospect data
            file_path: Optional path to save CSV file
        
        Returns:
            Path to saved file
        """
        try:
            if not file_path:
                file_path = "data/prospect_database.csv"
            
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Backup existing file
            if file_path.exists():
                backup_path = file_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                file_path.rename(backup_path)
                self.logger.info(f"📄 Backed up existing database to: {backup_path}")
            
            # Save new file
            df.to_csv(file_path, index=False)
            
            self.logger.info(f"💾 Saved prospect database: {file_path} | Records: {len(df)}")
            
            return str(file_path)
            
        except Exception as e:
            error_msg = f"Failed to save prospect database: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            raise
    
    def process_api_data(self, api_data: Dict[str, Any], data_source: str) -> Dict[str, Any]:
        """
        Process and standardize data from API sources
        
        Args:
            api_data: Raw data from API
            data_source: Source of the data (hubspot, openai, highergov)
        
        Returns:
            Processed and standardized data
        """
        try:
            processed_data = {}
            
            if data_source == "hubspot":
                # Process HubSpot company data
                properties = api_data.get("properties", {})
                processed_data = {
                    "name": properties.get("name"),
                    "domain": properties.get("domain"),
                    "website": properties.get("website"),
                    "industry": properties.get("industry"),
                    "country": properties.get("country"),
                    "state": properties.get("state"),
                    "city": properties.get("city"),
                    "employee_count": self._safe_int(properties.get("numberofemployees")),
                    "annual_revenue": self._safe_float(properties.get("annualrevenue")),
                    "phone": properties.get("phone"),
                    "description": properties.get("description"),
                    "hubspot_id": api_data.get("id"),
                    "atomus_score": self._safe_float(properties.get("atomus_score")),
                    "defense_contract_score": self._safe_float(properties.get("defense_contract_score")),
                    "technology_relevance_score": self._safe_float(properties.get("technology_relevance_score")),
                    "compliance_indicators_score": self._safe_float(properties.get("compliance_indicators_score")),
                    "tier_classification": properties.get("tier_classification"),
                    "last_research_date": properties.get("last_research_date"),
                    "research_summary": properties.get("research_summary"),
                    "contract_history": properties.get("contract_history"),
                    "technology_keywords_found": properties.get("technology_keywords_found"),
                }
            
            elif data_source == "highergov":
                # Process HigherGov analysis data
                processed_data = {
                    "name": api_data.get("company_name"),
                    "defense_contract_score": api_data.get("defense_contractor_score"),
                    "cage_code": api_data.get("identifiers", {}).get("cage_code"),
                    "duns_number": api_data.get("identifiers", {}).get("duns_number"),
                    "contract_history": json.dumps(api_data.get("contract_analysis", {})),
                }
            
            elif data_source == "openai":
                # Process OpenAI research data
                processed_data = {
                    "name": api_data.get("company_name"),
                    "research_summary": api_data.get("content", "")[:1000],  # Limit length
                    "last_research_date": api_data.get("metadata", {}).get("timestamp", "").split("T")[0],
                }
            
            # Add metadata
            processed_data["data_source"] = data_source
            processed_data["updated_date"] = datetime.now().isoformat()
            
            # Remove None values
            processed_data = {k: v for k, v in processed_data.items() if v is not None}
            
            return processed_data
            
        except Exception as e:
            error_msg = f"Failed to process {data_source} API data: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            return {}
    
    def calculate_data_quality_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate data quality score for a company record
        
        Args:
            data: Company data dictionary
        
        Returns:
            Data quality score (0-100)
        """
        try:
            quality_factors = {
                "name": 10,  # Essential
                "website": 8,
                "industry": 8,
                "employee_count": 6,
                "annual_revenue": 6,
                "description": 5,
                "country": 4,
                "state": 3,
                "city": 3,
                "phone": 3,
                "atomus_score": 8,
                "defense_contract_score": 8,
                "research_summary": 6,
                "cage_code": 5,
                "duns_number": 5,
            }
            
            total_possible = sum(quality_factors.values())
            achieved_score = 0
            
            for field, weight in quality_factors.items():
                value = data.get(field)
                if value is not None and str(value).strip():
                    achieved_score += weight
            
            quality_score = (achieved_score / total_possible) * 100
            
            return round(quality_score, 1)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Could not calculate data quality score: {str(e)}")
            return 0.0
    
    # UTILITY METHODS
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        if not url:
            return False
        
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(url) is not None
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL format"""
        if not url:
            return ""
        
        url = url.strip().lower()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        return url
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url:
            return ""
        
        url = self._normalize_url(url)
        domain_pattern = re.compile(r'https?://(?:www\.)?([^/]+)')
        match = domain_pattern.match(url)
        
        return match.group(1) if match else ""
    
    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name for deduplication"""
        if not name:
            return ""
        
        # Convert to lowercase and remove common suffixes
        normalized = name.lower().strip()
        normalized = re.sub(r'\s+(inc\.?|llc|corp\.?|corporation|ltd\.?|limited)\s*$', '', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove special characters
        normalized = re.sub(r'\s+', ' ', normalized).strip()  # Normalize whitespace
        
        return normalized
    
    def _merge_company_data(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two company records, keeping the most complete data"""
        merged = existing.copy()
        
        for key, value in new.items():
            if value is not None and str(value).strip():
                if key not in merged or not merged[key] or str(merged[key]).strip() == "":
                    merged[key] = value
                elif key in ["description", "research_summary", "contract_history"] and len(str(value)) > len(str(merged[key])):
                    # Keep longer text fields
                    merged[key] = value
        
        merged["updated_date"] = datetime.now().isoformat()
        
        return merged
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int"""
        if value is None or value == "":
            return None
        try:
            return int(float(str(value).replace(",", "")))
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None or value == "":
            return None
        try:
            return float(str(value).replace(",", "").replace("$", ""))
        except (ValueError, TypeError):
            return None
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get data processing statistics"""
        if self.stats["records_processed"] > 0:
            self.stats["data_quality_score"] = (self.stats["records_validated"] / self.stats["records_processed"]) * 100
        
        return {
            **self.stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def log_stats_summary(self):
        """Log a summary of data processing statistics"""
        stats = self.get_processing_stats()
        self.logger.info("📊 DATA PROCESSING STATS:")
        self.logger.info(f"   Records processed: {stats['records_processed']}")
        self.logger.info(f"   Records validated: {stats['records_validated']}")
        self.logger.info(f"   Records rejected: {stats['records_rejected']}")
        self.logger.info(f"   Duplicates found: {stats['duplicates_found']}")
        self.logger.info(f"   Data quality score: {stats['data_quality_score']:.1f}%")


def create_data_processor() -> AtomustamDataProcessor:
    """
    Factory function to create a data processor
    
    Returns:
        Configured data processor
    """
    return AtomustamDataProcessor()


if __name__ == "__main__":
    # Test the data processor
    from .utils import log_system_info, log_system_shutdown
    
    log_system_info()
    
    try:
        processor = create_data_processor()
        
        # Test data validation
        test_company = {
            "name": "Test Company Inc.",
            "website": "https://testcompany.com",
            "industry": "Technology",
            "employee_count": 150,
            "annual_revenue": 5000000
        }
        
        is_valid, errors = processor.validate_company_data(test_company)
        print(f"Validation result: {is_valid} | Errors: {errors}")
        
        # Test data cleaning
        cleaned_data = processor.clean_and_normalize_data(test_company)
        print(f"Cleaned data: {cleaned_data}")
        
        # Test data quality scoring
        quality_score = processor.calculate_data_quality_score(cleaned_data)
        print(f"Data quality score: {quality_score}")
        
        # Log final stats
        processor.log_stats_summary()
        
    except Exception as e:
        logger = get_logger()
        logger.error(f"Data processor test failed: {str(e)}")
        
    finally:
        log_system_shutdown()
