"""
Atomus TAM Research - OpenAI API Integration
This module provides comprehensive OpenAI API integration for AI-powered research
"""

import os
import json
import time
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path

import openai
from openai import OpenAI

from ..utils import (
    get_logger,
    get_api_logger,
    get_performance_tracker,
    get_error_handler,
    APIError,
    DataValidationError,
    retry_with_backoff,
    validate_required_fields
)


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI API client"""
    api_key: str
    model: str = "gpt-4"
    max_tokens: int = 2000
    temperature: float = 0.3
    rate_limit_per_minute: int = 60
    max_retries: int = 3
    timeout: int = 120


class AtomustamOpenAIClient:
    """
    Comprehensive OpenAI API client for Atomus TAM Research
    
    This client provides:
    - Company research automation using configurable prompts
    - Multiple research types (basic, deep, specialized)
    - Integration with research_prompts.yaml configuration
    - Batch processing capabilities
    - Comprehensive error handling and logging
    - Token usage tracking and cost estimation
    """
    
    def __init__(self, config: OpenAIConfig = None):
        self.logger = get_logger("openai_client")
        self.api_logger = get_api_logger()
        self.performance_tracker = get_performance_tracker()
        self.error_handler = get_error_handler()
        
        # Load configuration
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env()
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.config.api_key)
        
        # Load research prompts
        self.research_prompts = self._load_research_prompts()
        
        # Track API usage and costs
        self.api_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost_estimate": 0.0,
            "research_sessions": 0,
            "companies_researched": 0,
            "errors": 0,
            "requests_by_type": {},
            "tokens_by_type": {}
        }
        
        self.logger.info(f"🤖 OpenAI client initialized | Model: {self.config.model} | "
                        f"Rate limit: {self.config.rate_limit_per_minute}/min")
    
    def _load_config_from_env(self) -> OpenAIConfig:
        """Load OpenAI configuration from environment variables"""
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise DataValidationError("OPENAI_API_KEY environment variable is required")
        
        return OpenAIConfig(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
            rate_limit_per_minute=int(os.getenv("OPENAI_RATE_LIMIT", "60")),
            max_retries=int(os.getenv("OPENAI_MAX_RETRIES", "3")),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "120"))
        )
    
    def _load_research_prompts(self) -> Dict[str, Any]:
        """Load research prompts from configuration file"""
        try:
            prompts_file = Path("config/research_prompts.yaml")
            if prompts_file.exists():
                with open(prompts_file, 'r', encoding='utf-8') as f:
                    prompts = yaml.safe_load(f)
                self.logger.info(f"✅ Loaded research prompts from {prompts_file}")
                return prompts
            else:
                self.logger.warning(f"⚠️ Research prompts file not found: {prompts_file}")
                return self._get_default_prompts()
        except Exception as e:
            self.logger.error(f"❌ Failed to load research prompts: {str(e)}")
            return self._get_default_prompts()
    
    def _get_default_prompts(self) -> Dict[str, Any]:
        """Get default research prompts if configuration file is not available"""
        return {
            "basic_research": {
                "company_overview": {
                    "template": "Research the company {company_name} and provide a comprehensive overview focusing on defense contracting, technology stack, and compliance posture. Provide findings in JSON format.",
                    "max_tokens": 2000,
                    "temperature": 0.3
                }
            }
        }
    
    def _handle_rate_limit(self):
        """Handle rate limiting for API calls"""
        time.sleep(60.0 / self.config.rate_limit_per_minute)
    
    def _track_api_call(self, operation: str, tokens_used: int, success: bool = True):
        """Track API call statistics and costs"""
        self.api_stats["total_requests"] += 1
        self.api_stats["total_tokens"] += tokens_used
        
        # Estimate cost (GPT-4 pricing: ~$0.03/1K tokens input, ~$0.06/1K tokens output)
        estimated_cost = (tokens_used / 1000) * 0.045  # Average cost
        self.api_stats["total_cost_estimate"] += estimated_cost
        
        if not success:
            self.api_stats["errors"] += 1
        
        # Track by operation type
        if operation not in self.api_stats["requests_by_type"]:
            self.api_stats["requests_by_type"][operation] = 0
            self.api_stats["tokens_by_type"][operation] = 0
        
        self.api_stats["requests_by_type"][operation] += 1
        self.api_stats["tokens_by_type"][operation] += tokens_used
        
        self.api_logger.log_api_call(
            "openai",
            operation,
            "POST",
            payload_size=tokens_used,
            success=success
        )
    
    @retry_with_backoff(max_retries=3, backoff_factor=2.0)
    def test_connection(self) -> Dict[str, Any]:
        """
        Test OpenAI API connection
        
        Returns:
            Dictionary with connection status and model information
        """
        try:
            self._handle_rate_limit()
            
            # Test with a simple completion
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "user", "content": "Respond with 'Connection successful' if you can read this."}
                ],
                max_tokens=50,
                temperature=0
            )
            
            tokens_used = response.usage.total_tokens
            self._track_api_call("test_connection", tokens_used, True)
            
            self.logger.info(f"✅ OpenAI connection successful | Model: {self.config.model} | "
                           f"Tokens used: {tokens_used}")
            
            return {
                "status": "connected",
                "model": self.config.model,
                "tokens_used": tokens_used,
                "response": response.choices[0].message.content,
                "connection_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            self._track_api_call("test_connection", 0, False)
            error_msg = f"OpenAI connection test failed: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "openai", "chat/completions"))
            raise
    
    def conduct_research(self, company_name: str, research_type: str = "basic", 
                        research_category: str = "company_overview", 
                        additional_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Conduct AI-powered research on a company
        
        Args:
            company_name: Name of the company to research
            research_type: Type of research ("basic", "deep", "specialized")
            research_category: Specific research category from prompts
            additional_context: Additional context and parameters
        
        Returns:
            Research results dictionary
        """
        try:
            validate_required_fields({"company_name": company_name}, ["company_name"], "Research request")
            
            self.performance_tracker.start_timing(f"research_{company_name}")
            
            # Get prompt configuration
            prompt_config = self._get_prompt_config(research_type, research_category)
            if not prompt_config:
                raise DataValidationError(f"Research configuration not found: {research_type}.{research_category}")
            
            # Prepare prompt with company name and context
            prompt = self._prepare_prompt(prompt_config, company_name, additional_context or {})
            
            # Configure API parameters
            max_tokens = prompt_config.get("max_tokens", self.config.max_tokens)
            temperature = prompt_config.get("temperature", self.config.temperature)
            
            self.logger.info(f"🔍 Starting {research_type} research: {company_name} | "
                           f"Category: {research_category}")
            
            self._handle_rate_limit()
            
            # Make API call
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert business intelligence researcher specializing in defense contractors and cybersecurity compliance. Provide accurate, detailed, and actionable research findings."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Process response
            tokens_used = response.usage.total_tokens
            research_content = response.choices[0].message.content
            
            # Track statistics
            self.api_stats["research_sessions"] += 1
            self.api_stats["companies_researched"] += 1
            self._track_api_call(f"research_{research_type}", tokens_used, True)
            
            # Prepare result
            result = {
                "company_name": company_name,
                "research_type": research_type,
                "research_category": research_category,
                "content": research_content,
                "metadata": {
                    "model": self.config.model,
                    "tokens_used": tokens_used,
                    "cost_estimate": (tokens_used / 1000) * 0.045,
                    "timestamp": datetime.now().isoformat(),
                    "prompt_config": prompt_config
                }
            }
            
            self.performance_tracker.end_timing(
                f"research_{company_name}",
                f"Tokens: {tokens_used} | Type: {research_type}"
            )
            
            self.logger.info(f"✅ Research completed: {company_name} | "
                           f"Tokens: {tokens_used} | "
                           f"Type: {research_type}")
            
            return result
            
        except Exception as e:
            self._track_api_call(f"research_{research_type}", 0, False)
            error_msg = f"Research failed for {company_name}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "openai", "research"))
            raise
    
    def batch_research(self, companies: List[str], research_type: str = "basic",
                      research_category: str = "quick_assessment") -> List[Dict[str, Any]]:
        """
        Conduct batch research on multiple companies
        
        Args:
            companies: List of company names to research
            research_type: Type of research to conduct
            research_category: Research category to use
        
        Returns:
            List of research results
        """
        self.logger.info(f"🚀 Starting batch research | Companies: {len(companies)} | "
                        f"Type: {research_type}")
        
        self.performance_tracker.start_timing("batch_research")
        
        results = []
        failed_companies = []
        
        for i, company in enumerate(companies, 1):
            try:
                self.logger.info(f"📋 Researching company {i}/{len(companies)}: {company}")
                
                result = self.conduct_research(
                    company_name=company,
                    research_type=research_type,
                    research_category=research_category
                )
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"❌ Failed to research {company}: {str(e)}")
                failed_companies.append(company)
                continue
        
        self.performance_tracker.end_timing(
            "batch_research",
            f"Completed: {len(results)}/{len(companies)} | Failed: {len(failed_companies)}"
        )
        
        if failed_companies:
            self.logger.warning(f"⚠️ Failed to research {len(failed_companies)} companies: {failed_companies}")
        
        return results
    
    def analyze_for_scoring(self, company_name: str, company_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze a company specifically for scoring purposes
        
        Args:
            company_name: Name of the company
            company_data: Existing company data to include in analysis
        
        Returns:
            Analysis results with scoring recommendations
        """
        try:
            # Load scoring keywords from config
            scoring_config = self._load_scoring_config()
            keywords = self._extract_keywords_for_prompt(scoring_config)
            
            # Prepare context
            context = {
                "keyword_list": keywords,
                "existing_data": company_data or {},
                "scoring_focus": "defense_contractor_likelihood, compliance_need, technology_relevance"
            }
            
            # Conduct specialized research for scoring
            result = self.conduct_research(
                company_name=company_name,
                research_type="basic_research",
                research_category="quick_assessment",
                additional_context=context
            )
            
            self.logger.info(f"🎯 Scoring analysis completed for {company_name}")
            
            return result
            
        except Exception as e:
            error_msg = f"Scoring analysis failed for {company_name}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "openai", "scoring_analysis"))
            raise
    
    def enrich_contact_data(self, contact_name: str, company_name: str, 
                           title: str = None) -> Dict[str, Any]:
        """
        Enrich contact data using AI research
        
        Args:
            contact_name: Name of the contact
            company_name: Company the contact works for
            title: Contact's job title
        
        Returns:
            Enriched contact information
        """
        try:
            context = {
                "contact_name": contact_name,
                "company_name": company_name,
                "title": title or "Unknown",
                "focus_areas": ["decision_maker_role", "cybersecurity_responsibility", "contact_information"]
            }
            
            result = self.conduct_research(
                company_name=f"{contact_name} at {company_name}",
                research_type="basic_research",
                research_category="company_overview",
                additional_context=context
            )
            
            self.logger.info(f"👤 Contact enrichment completed: {contact_name} at {company_name}")
            
            return result
            
        except Exception as e:
            error_msg = f"Contact enrichment failed for {contact_name}: {str(e)}"
            self.error_handler.handle_error(APIError(error_msg, "openai", "contact_enrichment"))
            raise
    
    # UTILITY METHODS
    
    def _get_prompt_config(self, research_type: str, research_category: str) -> Optional[Dict[str, Any]]:
        """Get prompt configuration for specific research type and category"""
        try:
            return self.research_prompts.get(research_type, {}).get(research_category)
        except Exception:
            return None
    
    def _prepare_prompt(self, prompt_config: Dict[str, Any], company_name: str, 
                       context: Dict[str, Any]) -> str:
        """Prepare prompt by substituting variables"""
        template = prompt_config.get("template", "")
        
        # Basic substitutions
        prompt = template.replace("{company_name}", company_name)
        prompt = prompt.replace("{current_date}", datetime.now().strftime("%Y-%m-%d"))
        
        # Context substitutions
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in prompt:
                if isinstance(value, (list, dict)):
                    prompt = prompt.replace(placeholder, json.dumps(value, indent=2))
                else:
                    prompt = prompt.replace(placeholder, str(value))
        
        return prompt
    
    def _load_scoring_config(self) -> Dict[str, Any]:
        """Load scoring configuration for keyword extraction"""
        try:
            config_file = Path("config/scoring_config.yaml")
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"⚠️ Could not load scoring config: {str(e)}")
        
        return {}
    
    def _extract_keywords_for_prompt(self, scoring_config: Dict[str, Any]) -> str:
        """Extract keywords from scoring config for use in prompts"""
        try:
            keywords = []
            keyword_config = scoring_config.get("keywords", {})
            
            for category, config in keyword_config.items():
                terms = config.get("terms", [])
                keywords.extend(terms)
            
            compliance_keywords = scoring_config.get("compliance_keywords", {})
            for category, config in compliance_keywords.items():
                terms = config.get("terms", [])
                keywords.extend(terms)
            
            return ", ".join(keywords[:20])  # Limit to first 20 keywords
            
        except Exception:
            return "defense contractor, NIST 800-171, CMMC, cybersecurity, compliance"
    
    def save_research_results(self, results: Union[Dict[str, Any], List[Dict[str, Any]]], 
                             filename: str = None) -> str:
        """
        Save research results to file
        
        Args:
            results: Research results to save
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
                filename = f"research_results_{timestamp}.json"
            
            filepath = results_dir / filename
            
            # Save results
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Research results saved: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            error_msg = f"Failed to save research results: {str(e)}"
            self.error_handler.handle_error(Exception(error_msg))
            raise
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return {
            **self.api_stats,
            "timestamp": datetime.now().isoformat(),
            "config": {
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }
        }
    
    def log_stats_summary(self):
        """Log a summary of API usage statistics"""
        stats = self.get_api_stats()
        self.logger.info("📊 OPENAI API STATS:")
        self.logger.info(f"   Total requests: {stats['total_requests']}")
        self.logger.info(f"   Total tokens: {stats['total_tokens']:,}")
        self.logger.info(f"   Estimated cost: ${stats['total_cost_estimate']:.2f}")
        self.logger.info(f"   Research sessions: {stats['research_sessions']}")
        self.logger.info(f"   Companies researched: {stats['companies_researched']}")
        self.logger.info(f"   Errors: {stats['errors']}")


def create_openai_client(api_key: str = None, model: str = None) -> AtomustamOpenAIClient:
    """
    Factory function to create an OpenAI client
    
    Args:
        api_key: Optional API key override
        model: Optional model override
    
    Returns:
        Configured OpenAI client
    """
    config = None
    if api_key or model:
        # Note: API key should be set via environment variable OPENAI_API_KEY
        base_config = OpenAIConfig(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model=model or "gpt-4"
        )
        config = base_config
    
    return AtomustamOpenAIClient(config)


if __name__ == "__main__":
    # Test the OpenAI client
    from ..utils import log_system_info, log_system_shutdown
    
    log_system_info()
    
    try:
        # Create client and test connection
        client = create_openai_client()
        
        # Test connection
        connection_info = client.test_connection()
        print(f"Connection successful: {connection_info}")
        
        # Test basic research
        research_result = client.conduct_research(
            company_name="Firestorm",
            research_type="basic_research",
            research_category="company_overview"
        )
        print(f"Research completed for Firestorm")
        
        # Test batch research with test companies
        test_companies = ["Firehawk", "Overland AI", "Kform"]
        batch_results = client.batch_research(test_companies, "basic_research", "quick_assessment")
        print(f"Batch research completed for {len(batch_results)} companies")
        
        # Save results
        all_results = [research_result] + batch_results
        saved_path = client.save_research_results(all_results, "test_research_results.json")
        print(f"Results saved to: {saved_path}")
        
        # Log final stats
        client.log_stats_summary()
        
    except Exception as e:
        logger = get_logger()
        logger.error(f"OpenAI client test failed: {str(e)}")
        
    finally:
        log_system_shutdown()
