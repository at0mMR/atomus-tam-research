"""
Atomus TAM Research - Scoring Engine Core
This module implements the core scoring algorithm for defense contractor assessment
"""

import re
import json
import yaml
import math
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, asdict

from .utils import (
    get_logger,
    get_performance_tracker,
    get_scoring_logger,
    get_error_handler,
    DataValidationError,
    ScoringError,
    validate_required_fields,
    safe_execute
)
from .data_processing import CompanyData, AtomustamDataProcessor


@dataclass
class ScoringResult:
    """Standardized scoring result structure"""
    company_name: str
    total_score: float
    tier_classification: str
    component_scores: Dict[str, float]
    keyword_matches: Dict[str, List[str]]
    scoring_factors: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: str


class AtomustamScoringEngine:
    """
    Comprehensive scoring engine for Atomus TAM Research
    
    This engine provides:
    - Weighted component scoring (Defense 35%, Technology 30%, Compliance 25%, Firmographics 10%)
    - Keyword-based scoring with fuzzy matching
    - Firmographic analysis and scoring
    - Tier classification (1-4)
    - Integration with API data sources
    - Comprehensive logging and error handling
    """
    
    def __init__(self, config_path: str = None):
        self.logger = get_logger("scoring_engine")
        self.scoring_logger = get_scoring_logger()
        self.performance_tracker = get_performance_tracker()
        self.error_handler = get_error_handler()
        
        # Load scoring configuration
        self.config = self._load_scoring_config(config_path)
        
        # Initialize data processor for integration
        self.data_processor = AtomustamDataProcessor()
        
        # Scoring statistics
        self.stats = {
            "companies_scored": 0,
            "tier_distribution": {"tier_1": 0, "tier_2": 0, "tier_3": 0, "tier_4": 0, "excluded": 0},
            "average_scores": {"total": 0.0, "defense": 0.0, "technology": 0.0, "compliance": 0.0, "firmographics": 0.0},
            "keyword_usage": {},
            "processing_time": 0.0
        }
        
        self.logger.info("🎯 Scoring engine initialized")
    
    def _load_scoring_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load scoring configuration from YAML or JSON files"""
        try:
            # Try YAML first (primary configuration)
            yaml_path = Path(config_path or "config/scoring_config.yaml")
            if yaml_path.exists():
                with open(yaml_path, 'r') as f:
                    config = yaml.safe_load(f)
                self.logger.info(f"✅ Loaded scoring config from: {yaml_path}")
                return config
            
            # Fall back to JSON configuration
            json_path = Path("data/scoring_weights.json")
            if json_path.exists():
                with open(json_path, 'r') as f:
                    config = json.load(f)
                self.logger.info(f"✅ Loaded scoring config from: {json_path}")
                return config
            
            # Use default configuration if no files found
            self.logger.warning("⚠️ No scoring config found, using defaults")
            return self._get_default_config()
            
        except Exception as e:
            error_msg = f"Failed to load scoring configuration: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default scoring configuration"""
        return {
            "scoring_weights": {
                "defense_contract_score": 0.35,
                "technology_relevance": 0.30,
                "compliance_indicators": 0.25,
                "firmographics": 0.10
            },
            "keywords": {
                "primary": {"points": 10, "terms": ["hypersonic", "nuclear", "propulsion", "defense manufacturing", "engineering services"]},
                "secondary": {"points": 7, "terms": ["drone", "UAS", "UAV", "UXS", "UUV"]},
                "specialized": {"points": 10, "terms": ["RF", "EW", "Electronic Warfare"]}
            },
            "tier_classification": {
                "tier_1": {"min_score": 90, "max_score": 100},
                "tier_2": {"min_score": 75, "max_score": 89},
                "tier_3": {"min_score": 60, "max_score": 74},
                "tier_4": {"min_score": 45, "max_score": 59},
                "excluded": {"min_score": 0, "max_score": 44}
            }
        }
    
    def score_company(self, company_data: Union[Dict[str, Any], CompanyData], 
                     additional_data: Dict[str, Any] = None) -> ScoringResult:
        """
        Score a company using the comprehensive Atomus algorithm
        
        Args:
            company_data: Company data (dict or CompanyData object)
            additional_data: Additional data from APIs (research, contracts, etc.)
        
        Returns:
            ScoringResult object with complete scoring analysis
        """
        try:
            # Convert to dict if CompanyData object
            if isinstance(company_data, CompanyData):
                company_dict = asdict(company_data)
            else:
                company_dict = company_data.copy()
            
            # Merge additional data
            if additional_data:
                company_dict.update(additional_data)
            
            company_name = company_dict.get("name", "Unknown Company")
            
            validate_required_fields(company_dict, ["name"], "Company scoring")
            
            self.performance_tracker.start_timing(f"scoring_{company_name}")
            
            self.logger.info(f"🎯 Scoring company: {company_name}")
            
            # Calculate component scores
            defense_score = self._calculate_defense_score(company_dict)
            technology_score = self._calculate_technology_score(company_dict)
            compliance_score = self._calculate_compliance_score(company_dict)
            firmographics_score = self._calculate_firmographics_score(company_dict)
            
            # Get scoring weights
            weights = self.config.get("scoring_weights", {})
            defense_weight = weights.get("defense_contract_score", 0.35)
            tech_weight = weights.get("technology_relevance", 0.30)
            compliance_weight = weights.get("compliance_indicators", 0.25)
            firmographics_weight = weights.get("firmographics", 0.10)
            
            # Calculate weighted total score
            total_score = (
                defense_score * defense_weight +
                technology_score * tech_weight +
                compliance_score * compliance_weight +
                firmographics_score * firmographics_weight
            )
            
            # Apply bonus multiplier if multiple high-value keywords found
            keyword_matches = self._extract_all_keyword_matches(company_dict)
            total_keywords = sum(len(matches) for matches in keyword_matches.values())
            
            if total_keywords >= 5:  # Bonus for companies with many relevant keywords
                bonus_multiplier = self.config.get("algorithm_parameters", {}).get("bonus_multiplier", 1.2)
                total_score = min(total_score * bonus_multiplier, 100)
                self.logger.debug(f"🎁 Applied bonus multiplier to {company_name}: {bonus_multiplier}")
            
            # Ensure score is within valid range
            total_score = max(0, min(100, total_score))
            
            # Determine tier classification
            tier_classification = self._classify_tier(total_score)
            
            # Prepare component scores
            component_scores = {
                "defense_contract_score": round(defense_score, 1),
                "technology_relevance_score": round(technology_score, 1),
                "compliance_indicators_score": round(compliance_score, 1),
                "firmographics_score": round(firmographics_score, 1),
                "total_score": round(total_score, 1)
            }
            
            # Extract scoring factors for analysis
            scoring_factors = self._extract_scoring_factors(company_dict, keyword_matches)
            
            # Create scoring result
            result = ScoringResult(
                company_name=company_name,
                total_score=round(total_score, 1),
                tier_classification=tier_classification,
                component_scores=component_scores,
                keyword_matches=keyword_matches,
                scoring_factors=scoring_factors,
                metadata={
                    "weights_used": weights,
                    "bonus_applied": total_keywords >= 5,
                    "total_keywords_found": total_keywords,
                    "scoring_algorithm_version": "1.0"
                },
                timestamp=datetime.now().isoformat()
            )
            
            # Update statistics
            self._update_scoring_stats(result)
            
            # Log scoring result
            key_factors = self._get_key_factors(scoring_factors, keyword_matches)
            self.scoring_logger.log_company_scoring(
                company_name, total_score, tier_classification, key_factors
            )
            
            self.scoring_logger.log_keyword_matches(company_name, keyword_matches)
            
            self.performance_tracker.end_timing(
                f"scoring_{company_name}",
                f"Score: {total_score:.1f} | Tier: {tier_classification}"
            )
            
            self.logger.info(f"✅ Scoring completed: {company_name} | "
                           f"Score: {total_score:.1f} | Tier: {tier_classification}")
            
            return result
            
        except Exception as e:
            error_msg = f"Scoring failed for {company_name}: {str(e)}"
            self.error_handler.handle_error(ScoringError(error_msg, company_name, company_dict))
            raise
    
    def batch_score_companies(self, companies: List[Union[Dict[str, Any], CompanyData]]) -> List[ScoringResult]:
        """
        Score multiple companies in batch
        
        Args:
            companies: List of company data
        
        Returns:
            List of ScoringResult objects
        """
        self.logger.info(f"🚀 Starting batch scoring | Companies: {len(companies)}")
        
        self.performance_tracker.start_timing("batch_scoring")
        
        results = []
        failed_companies = []
        
        for i, company_data in enumerate(companies, 1):
            try:
                company_name = company_data.get("name", f"Company_{i}") if isinstance(company_data, dict) else company_data.name
                self.logger.info(f"📋 Scoring company {i}/{len(companies)}: {company_name}")
                
                result = self.score_company(company_data)
                results.append(result)
                
            except Exception as e:
                company_name = "Unknown"
                if isinstance(company_data, dict):
                    company_name = company_data.get("name", "Unknown")
                elif isinstance(company_data, CompanyData):
                    company_name = company_data.name
                
                self.logger.error(f"❌ Failed to score {company_name}: {str(e)}")
                failed_companies.append(company_name)
                continue
        
        self.performance_tracker.end_timing(
            "batch_scoring",
            f"Completed: {len(results)}/{len(companies)} | Failed: {len(failed_companies)}"
        )
        
        if failed_companies:
            self.logger.warning(f"⚠️ Failed to score {len(failed_companies)} companies: {failed_companies}")
        
        # Log batch statistics
        if results:
            avg_score = sum(r.total_score for r in results) / len(results)
            tier_counts = {}
            for result in results:
                tier = result.tier_classification
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            self.logger.info(f"📊 BATCH SCORING SUMMARY:")
            self.logger.info(f"   Companies scored: {len(results)}")
            self.logger.info(f"   Average score: {avg_score:.1f}")
            self.logger.info(f"   Tier distribution: {tier_counts}")
        
        return results
    
    def _calculate_defense_score(self, company_dict: Dict[str, Any]) -> float:
        """Calculate defense contract score component"""
        try:
            score = 0.0
            
            # Use existing defense contract score if available (from HigherGov)
            if company_dict.get("defense_contract_score") is not None:
                score = float(company_dict["defense_contract_score"])
                self.logger.debug(f"Using existing defense score: {score}")
                return min(100, max(0, score))
            
            # Calculate based on available indicators
            indicators = {
                "cage_code": 15,  # Has CAGE code
                "duns_number": 10,  # Has DUNS number
                "contract_history": 20,  # Has contract history
                "defense_keywords": 25,  # Defense-related keywords in description
                "industry_match": 30  # Defense/aerospace industry
            }
            
            # Check for CAGE code
            if company_dict.get("cage_code"):
                score += indicators["cage_code"]
                self.logger.debug(f"Added points for CAGE code: {indicators['cage_code']}")
            
            # Check for DUNS number
            if company_dict.get("duns_number"):
                score += indicators["duns_number"]
                self.logger.debug(f"Added points for DUNS number: {indicators['duns_number']}")
            
            # Check for contract history
            if company_dict.get("contract_history"):
                score += indicators["contract_history"]
                self.logger.debug(f"Added points for contract history: {indicators['contract_history']}")
            
            # Check for defense keywords in description
            defense_keywords = ["defense", "military", "aerospace", "DoD", "government", "contractor"]
            description = (company_dict.get("description", "") + " " + 
                         company_dict.get("research_summary", "")).lower()
            
            found_keywords = [kw for kw in defense_keywords if kw in description]
            if found_keywords:
                keyword_score = min(len(found_keywords) * 5, indicators["defense_keywords"])
                score += keyword_score
                self.logger.debug(f"Added points for defense keywords: {keyword_score} | Keywords: {found_keywords}")
            
            # Check industry classification
            industry = company_dict.get("industry", "").lower()
            defense_industries = ["defense", "aerospace", "military", "manufacturing", "engineering"]
            
            if any(di in industry for di in defense_industries):
                score += indicators["industry_match"]
                self.logger.debug(f"Added points for defense industry: {indicators['industry_match']}")
            
            return min(100, score)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Defense scoring failed: {str(e)}")
            return 0.0
    
    def _calculate_technology_score(self, company_dict: Dict[str, Any]) -> float:
        """Calculate technology relevance score component"""
        try:
            score = 0.0
            
            # Use existing technology score if available
            if company_dict.get("technology_relevance_score") is not None:
                score = float(company_dict["technology_relevance_score"])
                self.logger.debug(f"Using existing technology score: {score}")
                return min(100, max(0, score))
            
            # Score based on technology keywords
            tech_keywords = self.config.get("technology_keywords", {})
            all_text = (
                company_dict.get("description", "") + " " +
                company_dict.get("research_summary", "") + " " +
                company_dict.get("technology_keywords_found", "") + " " +
                company_dict.get("industry", "")
            ).lower()
            
            for category, config in tech_keywords.items():
                category_points = config.get("points", 8)
                keywords = config.get("keywords", [])
                
                found_keywords = [kw for kw in keywords if kw.lower() in all_text]
                if found_keywords:
                    category_score = min(len(found_keywords) * (category_points / len(keywords)) * 10, category_points)
                    score += category_score
                    self.logger.debug(f"Added {category_score:.1f} points for {category}: {found_keywords}")
            
            # Bonus for technology-focused companies
            tech_indicators = ["software", "AI", "IoT", "cloud", "cybersecurity", "automation", "digital"]
            found_tech_indicators = [ti for ti in tech_indicators if ti.lower() in all_text]
            
            if found_tech_indicators:
                tech_bonus = min(len(found_tech_indicators) * 5, 20)
                score += tech_bonus
                self.logger.debug(f"Added technology bonus: {tech_bonus} | Indicators: {found_tech_indicators}")
            
            return min(100, score)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Technology scoring failed: {str(e)}")
            return 0.0
    
    def _calculate_compliance_score(self, company_dict: Dict[str, Any]) -> float:
        """Calculate compliance indicators score component"""
        try:
            score = 0.0
            
            # Use existing compliance score if available
            if company_dict.get("compliance_indicators_score") is not None:
                score = float(company_dict["compliance_indicators_score"])
                self.logger.debug(f"Using existing compliance score: {score}")
                return min(100, max(0, score))
            
            # Score based on compliance keywords
            compliance_keywords = self.config.get("compliance_keywords", {})
            all_text = (
                company_dict.get("description", "") + " " +
                company_dict.get("research_summary", "") + " " +
                company_dict.get("technology_keywords_found", "")
            ).lower()
            
            for category, config in compliance_keywords.items():
                category_points = config.get("points", 10)
                keywords = config.get("terms", [])
                
                found_keywords = [kw for kw in keywords if kw.lower() in all_text]
                if found_keywords:
                    category_score = min(len(found_keywords) * (category_points / 2), category_points)
                    score += category_score
                    self.logger.debug(f"Added {category_score:.1f} points for {category} compliance: {found_keywords}")
            
            # Bonus for existing certifications or compliance mentions
            cert_indicators = ["ISO", "SOC", "FedRAMP", "certified", "compliant", "audit", "assessment"]
            found_certs = [ci for ci in cert_indicators if ci.lower() in all_text]
            
            if found_certs:
                cert_bonus = min(len(found_certs) * 8, 25)
                score += cert_bonus
                self.logger.debug(f"Added certification bonus: {cert_bonus} | Indicators: {found_certs}")
            
            return min(100, score)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Compliance scoring failed: {str(e)}")
            return 0.0
    
    def _calculate_firmographics_score(self, company_dict: Dict[str, Any]) -> float:
        """Calculate firmographics score component"""
        try:
            score = 0.0
            
            # Employee count scoring
            employee_count = company_dict.get("employee_count")
            if employee_count:
                employee_ranges = self.config.get("firmographics", {}).get("employee_count", {}).get("ranges", [])
                for range_config in employee_ranges:
                    if range_config["min"] <= employee_count <= range_config["max"]:
                        score += range_config["points"]
                        self.logger.debug(f"Added {range_config['points']} points for employee count: {employee_count}")
                        break
            
            # Revenue scoring
            annual_revenue = company_dict.get("annual_revenue")
            if annual_revenue:
                revenue_ranges = self.config.get("firmographics", {}).get("revenue", {}).get("ranges", [])
                for range_config in revenue_ranges:
                    if range_config["min"] <= annual_revenue <= range_config["max"]:
                        score += range_config["points"]
                        self.logger.debug(f"Added {range_config['points']} points for revenue: ${annual_revenue:,.0f}")
                        break
            
            # Industry NAICS code scoring
            industry = company_dict.get("industry", "").lower()
            naics_scoring = self.config.get("firmographics", {}).get("industry_codes", {}).get("NAICS", {})
            
            # Map industry to NAICS-like scoring
            industry_mappings = {
                "aircraft": 15, "aerospace": 15, "defense": 12, "engineering": 12,
                "manufacturing": 10, "technology": 8, "software": 8
            }
            
            for industry_key, points in industry_mappings.items():
                if industry_key in industry:
                    score += points
                    self.logger.debug(f"Added {points} points for industry match: {industry_key}")
                    break
            
            # Location bonus (US-based companies)
            if company_dict.get("country", "").lower() in ["united states", "usa", "us"]:
                score += 5
                self.logger.debug("Added 5 points for US location")
            
            return min(100, score)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Firmographics scoring failed: {str(e)}")
            return 0.0
    
    def _extract_all_keyword_matches(self, company_dict: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract all keyword matches across categories"""
        keyword_matches = {}
        
        # Combine all text fields for keyword searching
        all_text = (
            company_dict.get("description", "") + " " +
            company_dict.get("research_summary", "") + " " +
            company_dict.get("technology_keywords_found", "") + " " +
            company_dict.get("industry", "") + " " +
            company_dict.get("name", "")
        ).lower()
        
        # Search for keywords in each category
        keywords_config = self.config.get("keywords", {})
        
        for category, config in keywords_config.items():
            if isinstance(config, dict) and "terms" in config:
                terms = config["terms"]
                found_terms = []
                
                for term in terms:
                    if self._keyword_matches(term, all_text):
                        found_terms.append(term)
                        # Update keyword usage statistics
                        if term not in self.stats["keyword_usage"]:
                            self.stats["keyword_usage"][term] = 0
                        self.stats["keyword_usage"][term] += 1
                
                if found_terms:
                    keyword_matches[category] = found_terms
        
        # Also check compliance and technology keywords
        for category_group in ["compliance_keywords", "technology_keywords"]:
            group_config = self.config.get(category_group, {})
            for subcategory, config in group_config.items():
                if isinstance(config, dict) and ("terms" in config or "keywords" in config):
                    terms = config.get("terms", config.get("keywords", []))
                    found_terms = []
                    
                    for term in terms:
                        if self._keyword_matches(term, all_text):
                            found_terms.append(term)
                    
                    if found_terms:
                        keyword_matches[f"{category_group}_{subcategory}"] = found_terms
        
        return keyword_matches
    
    def _keyword_matches(self, keyword: str, text: str) -> bool:
        """Check if keyword matches text with fuzzy matching support"""
        # Exact match
        if keyword.lower() in text.lower():
            return True
        
        # Fuzzy matching if enabled
        algorithm_params = self.config.get("algorithm_parameters", {})
        if algorithm_params.get("keyword_matching", {}).get("fuzzy_matching", True):
            # Simple fuzzy matching - check for partial matches
            keyword_parts = keyword.lower().split()
            if len(keyword_parts) > 1:
                # For multi-word keywords, check if most parts are present
                matches = sum(1 for part in keyword_parts if part in text.lower())
                return matches >= len(keyword_parts) * 0.8
            else:
                # For single words, check for stem matches
                keyword_stem = keyword_parts[0][:4]  # Simple stemming
                return keyword_stem in text.lower()
        
        return False
    
    def _classify_tier(self, total_score: float) -> str:
        """Classify company into tier based on total score"""
        tier_config = self.config.get("tier_classification", {})
        
        for tier, config in tier_config.items():
            min_score = config.get("min_score", 0)
            max_score = config.get("max_score", 100)
            
            if min_score <= total_score <= max_score:
                return tier
        
        # Default to excluded if no tier matches
        return "excluded"
    
    def _extract_scoring_factors(self, company_dict: Dict[str, Any], 
                                keyword_matches: Dict[str, List[str]]) -> Dict[str, Any]:
        """Extract key factors that influenced the scoring"""
        return {
            "has_cage_code": bool(company_dict.get("cage_code")),
            "has_duns_number": bool(company_dict.get("duns_number")),
            "has_contract_history": bool(company_dict.get("contract_history")),
            "has_research_summary": bool(company_dict.get("research_summary")),
            "employee_count": company_dict.get("employee_count"),
            "annual_revenue": company_dict.get("annual_revenue"),
            "industry": company_dict.get("industry"),
            "country": company_dict.get("country"),
            "total_keywords_found": sum(len(matches) for matches in keyword_matches.values()),
            "keyword_categories_found": list(keyword_matches.keys()),
            "is_defense_industry": any(term in company_dict.get("industry", "").lower() 
                                    for term in ["defense", "aerospace", "military"]),
            "has_technology_keywords": any("technology" in category for category in keyword_matches.keys())
        }
    
    def _get_key_factors(self, scoring_factors: Dict[str, Any], 
                        keyword_matches: Dict[str, List[str]]) -> List[str]:
        """Get key factors for logging"""
        factors = []
        
        if scoring_factors.get("is_defense_industry"):
            factors.append("defense industry")
        
        if scoring_factors.get("has_cage_code"):
            factors.append("CAGE code")
        
        if scoring_factors.get("has_contract_history"):
            factors.append("contract history")
        
        # Add top keyword categories
        keyword_categories = list(keyword_matches.keys())[:3]
        factors.extend(keyword_categories)
        
        return factors[:5]  # Limit to top 5 factors
    
    def _update_scoring_stats(self, result: ScoringResult):
        """Update scoring statistics"""
        self.stats["companies_scored"] += 1
        
        # Update tier distribution
        tier = result.tier_classification
        if tier in self.stats["tier_distribution"]:
            self.stats["tier_distribution"][tier] += 1
        
        # Update average scores
        component_scores = result.component_scores
        total_companies = self.stats["companies_scored"]
        
        # Calculate running averages
        for component, score in component_scores.items():
            if component in self.stats["average_scores"]:
                current_avg = self.stats["average_scores"][component]
                new_avg = (current_avg * (total_companies - 1) + score) / total_companies
                self.stats["average_scores"][component] = round(new_avg, 1)
    
    def get_scoring_stats(self) -> Dict[str, Any]:
        """Get comprehensive scoring statistics"""
        return {
            **self.stats,
            "timestamp": datetime.now().isoformat(),
            "config_version": self.config.get("scoring_algorithm", {}).get("version", "1.0")
        }
    
    def save_scoring_results(self, results: List[ScoringResult], filename: str = None) -> str:
        """Save scoring results to file"""
        try:
            results_dir = Path("data/research_results")
            results_dir.mkdir(parents=True, exist_ok=True)
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"scoring_results_{timestamp}.json"
            
            filepath = results_dir / filename
            
            # Convert results to serializable format
            serializable_results = []
            for result in results:
                result_dict = asdict(result)
                serializable_results.append(result_dict)
            
            # Save results with metadata
            output_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_companies": len(results),
                    "scoring_algorithm_version": "1.0",
                    "config_used": self.config.get("scoring_algorithm", {}),
                    "statistics": self.get_scoring_stats()
                },
                "results": serializable_results
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Scoring results saved: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            error_msg = f"Failed to save scoring results: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            raise
    
    def log_stats_summary(self):
        """Log summary of scoring statistics"""
        stats = self.get_scoring_stats()
        self.logger.info("📊 SCORING ENGINE STATS:")
        self.logger.info(f"   Companies scored: {stats['companies_scored']}")
        self.logger.info(f"   Average total score: {stats['average_scores']['total']}")
        self.logger.info(f"   Tier distribution: {stats['tier_distribution']}")
        
        if stats["keyword_usage"]:
            top_keywords = sorted(stats["keyword_usage"].items(), key=lambda x: x[1], reverse=True)[:5]
            self.logger.info(f"   Top keywords: {dict(top_keywords)}")


def create_scoring_engine(config_path: str = None) -> AtomustamScoringEngine:
    """
    Factory function to create a scoring engine
    
    Args:
        config_path: Optional path to scoring configuration file
    
    Returns:
        Configured scoring engine
    """
    return AtomustamScoringEngine(config_path)


if __name__ == "__main__":
    # Test the scoring engine
    from .utils import log_system_info, log_system_shutdown
    from .data_processing import create_data_processor
    import pandas as pd
    
    log_system_info()
    
    try:
        # Create scoring engine
        engine = create_scoring_engine()
        
        # Load test companies from prospect database
        data_processor = create_data_processor()
        df = data_processor.load_prospect_database()
        
        if not df.empty:
            # Test scoring with first few companies
            test_companies = df.head(3).to_dict('records')
            
            print(f"Testing scoring with {len(test_companies)} companies...")
            
            # Score companies individually
            results = []
            for company_data in test_companies:
                result = engine.score_company(company_data)
                results.append(result)
                print(f"Scored {result.company_name}: {result.total_score} ({result.tier_classification})")
            
            # Test batch scoring
            batch_results = engine.batch_score_companies(test_companies)
            print(f"Batch scoring completed: {len(batch_results)} companies")
            
            # Save results
            saved_path = engine.save_scoring_results(batch_results, "test_scoring_results.json")
            print(f"Results saved to: {saved_path}")
            
            # Log final stats
            engine.log_stats_summary()
        
        else:
            print("No test companies found in prospect database")
        
    except Exception as e:
        logger = get_logger()
        logger.error(f"Scoring engine test failed: {str(e)}")
        
    finally:
        log_system_shutdown()
