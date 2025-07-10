"""
Atomus TAM Research - Scoring Engine Test
This script demonstrates the scoring engine with the 13 test companies
"""

import json
import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from scoring_engine import AtomScoringEngine
from data_processing import AtomDataProcessor
from utils import get_logger, log_system_info, log_system_shutdown, get_performance_tracker


def test_scoring_engine_with_prospect_database():
    """
    Test the scoring engine with all 13 companies from the prospect database
    """
    logger = get_logger()
    tracker = get_performance_tracker()
    
    log_system_info()
    
    try:
        tracker.start_timing("scoring_engine_test")
        
        # Initialize components
        logger.info("🚀 Initializing scoring engine and data processor...")
        
        scoring_engine = AtomScoringEngine()
        data_processor = AtomDataProcessor()
        
        # Load prospect database
        logger.info("📖 Loading prospect database...")
        df = data_processor.load_prospect_database()
        
        if not df:
            logger.error("❌ No companies found in prospect database")
            return
        
        logger.info(f"✅ Loaded {len(df)} companies from prospect database")
        
        # Process and score companies
        logger.info("🎯 Starting scoring of all companies...")
        scoring_results = []
        
        for company_data in df:
            try:
                # Validate data
                validation_result = data_processor.validate_company_data(company_data)
                if not validation_result['is_valid']:
                    logger.warning(f"⚠️ Validation issues for {company_data.get('name')}: {validation_result['errors']}")
                
                # Score the company
                result = scoring_engine.calculate_company_score(company_data)
                scoring_results.append(result)
                
                logger.info(f"✅ Scored {company_data['name']}: {result['total_score']:.1f} ({result['tier_classification']})")
                
            except Exception as e:
                logger.error(f"❌ Failed to score {company_data.get('name', 'Unknown')}: {str(e)}")
        
        logger.info(f"✅ Scoring complete | {len(scoring_results)} companies scored")
        
        # Analyze and report results
        logger.info("📊 Analyzing scoring results...")
        
        # Sort by score (highest first)
        sorted_results = sorted(scoring_results, key=lambda x: x['total_score'], reverse=True)
        
        # Calculate statistics
        total_companies = len(scoring_results)
        avg_score = sum(r['total_score'] for r in scoring_results) / total_companies
        
        # Tier distribution
        tier_counts = {}
        for result in scoring_results:
            tier = result['tier_classification']
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Component score averages
        component_averages = {
            "defense": sum(r['component_scores'].get("defense_contract_score", 0) for r in scoring_results) / total_companies,
            "technology": sum(r['component_scores'].get("technology_relevance", 0) for r in scoring_results) / total_companies,
            "compliance": sum(r['component_scores'].get("compliance_indicators", 0) for r in scoring_results) / total_companies,
            "firmographics": sum(r['component_scores'].get("firmographics", 0) for r in scoring_results) / total_companies
        }
        
        # Most common keywords found
        all_keywords = {}
        for result in scoring_results:
            for category, keywords in result['keywords_found'].items():
                for keyword in keywords:
                    all_keywords[keyword] = all_keywords.get(keyword, 0) + 1
        
        top_keywords = sorted(all_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Create comprehensive test report
        test_report = {
            "test_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_companies": total_companies,
                "scoring_algorithm_version": "1.0",
                "test_type": "prospect_database_scoring"
            },
            "summary_statistics": {
                "average_score": round(avg_score, 1),
                "highest_score": sorted_results[0]['total_score'] if sorted_results else 0,
                "lowest_score": sorted_results[-1]['total_score'] if sorted_results else 0,
                "tier_distribution": tier_counts,
                "component_averages": {k: round(v, 1) for k, v in component_averages.items()}
            },
            "top_companies": [
                {
                    "rank": i + 1,
                    "company_name": result.get('company_name', 'Unknown'),
                    "total_score": result['total_score'],
                    "tier": result['tier_classification'],
                    "keywords_found": sum(len(keywords) for keywords in result['keywords_found'].values())
                }
                for i, result in enumerate(sorted_results[:10])
            ],
            "tier_analysis": {},
            "keyword_analysis": {
                "top_keywords": dict(top_keywords),
                "total_unique_keywords": len(all_keywords),
                "keyword_distribution": {}
            },
            "detailed_results": [
                {
                    "company_name": result.get('company_name', 'Unknown'),
                    "total_score": result['total_score'],
                    "tier_classification": result['tier_classification'],
                    "component_scores": result['component_scores'],
                    "keywords_found": result['keywords_found']
                }
                for result in sorted_results
            ]
        }
        
        # Analyze each tier
        for tier in ["tier_1", "tier_2", "tier_3", "tier_4", "excluded"]:
            tier_companies = [r for r in scoring_results if r['tier_classification'] == tier]
            if tier_companies:
                tier_avg = sum(r['total_score'] for r in tier_companies) / len(tier_companies)
                test_report["tier_analysis"][tier] = {
                    "count": len(tier_companies),
                    "average_score": round(tier_avg, 1),
                    "companies": [r.get('company_name', 'Unknown') for r in tier_companies]
                }
        
        # Analyze keyword distribution by category
        keyword_categories = {}
        for result in scoring_results:
            for category, keywords in result['keywords_found'].items():
                if category not in keyword_categories:
                    keyword_categories[category] = 0
                keyword_categories[category] += len(keywords)
        
        test_report["keyword_analysis"]["keyword_distribution"] = keyword_categories
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive test report
        report_file = Path(f"../data/research_results/scoring_test_report_{timestamp}.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(test_report, f, indent=2, ensure_ascii=False)
        
        # Save detailed scoring results
        results_file = Path(f"../data/research_results/test_scoring_all_companies_{timestamp}.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(scoring_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📋 Test report saved: {report_file}")
        logger.info(f"💾 Scoring results saved: {results_file}")
        
        # Print detailed console summary
        print("\\n" + "="*80)
        print("ATOMUS TAM RESEARCH - SCORING ENGINE TEST RESULTS")
        print("="*80)
        print(f"Total Companies Scored: {total_companies}")
        print(f"Average Score: {avg_score:.1f}/100")
        print(f"Score Range: {sorted_results[-1]['total_score']:.1f} - {sorted_results[0]['total_score']:.1f}")
        
        print(f"\\nTIER DISTRIBUTION:")
        for tier, count in tier_counts.items():
            percentage = (count / total_companies) * 100
            tier_display = tier.replace("_", " ").title()
            print(f"  {tier_display}: {count} companies ({percentage:.1f}%)")
        
        print(f"\\nCOMPONENT SCORE AVERAGES:")
        print(f"  Defense Contracts: {component_averages['defense']:.1f}/100")
        print(f"  Technology Relevance: {component_averages['technology']:.1f}/100")
        print(f"  Compliance Indicators: {component_averages['compliance']:.1f}/100")
        print(f"  Firmographics: {component_averages['firmographics']:.1f}/100")
        
        print(f"\\nTOP 5 COMPANIES:")
        for i, result in enumerate(sorted_results[:5], 1):
            tier_display = result['tier_classification'].replace("_", " ").title()
            print(f"  {i}. {result.get('company_name', 'Unknown')}: {result['total_score']:.1f} ({tier_display})")
        
        print(f"\\nTOP KEYWORDS FOUND:")
        for keyword, count in top_keywords[:8]:
            print(f"  {keyword}: {count} companies")
        
        print(f"\\nTIER 1 COMPANIES (Immediate Outreach Priority):")
        tier_1_companies = [r for r in scoring_results if r['tier_classification'] == "tier_1"]
        if tier_1_companies:
            for company in tier_1_companies:
                print(f"  • {company.get('company_name', 'Unknown')}: {company['total_score']:.1f}")
        else:
            print("  No companies qualified for Tier 1")
        
        print(f"\\nTIER 2 COMPANIES (High-Value Prospects):")
        tier_2_companies = [r for r in scoring_results if r['tier_classification'] == "tier_2"]
        if tier_2_companies:
            for company in tier_2_companies[:5]:  # Show top 5
                print(f"  • {company.get('company_name', 'Unknown')}: {company['total_score']:.1f}")
            if len(tier_2_companies) > 5:
                print(f"  ... and {len(tier_2_companies) - 5} more")
        else:
            print("  No companies qualified for Tier 2")
        
        print(f"\\nFILES GENERATED:")
        print(f"  Test Report: {report_file}")
        print(f"  Detailed Results: {results_file}")
        
        print("="*80)
        
        tracker.end_timing("scoring_engine_test", f"Scored {len(scoring_results)} companies")
        
        return test_report
        
    except Exception as e:
        logger.error(f"❌ Scoring engine test failed: {str(e)}")
        raise
    finally:
        log_system_shutdown()


def test_individual_company_scoring():
    """
    Test scoring individual companies with detailed breakdown
    """
    logger = get_logger()
    logger.info("🧪 Testing individual company scoring...")
    
    # Create scoring engine
    scoring_engine = AtomScoringEngine()
    
    # Test with a sample company (enhanced with additional data)
    test_company = {
        "name": "Advanced Defense Systems Corp",
        "website": "https://advanceddefense.com",
        "industry": "Defense Manufacturing",
        "description": "Advanced defense manufacturing specializing in hypersonic propulsion systems, UAV technologies, and cybersecurity solutions for DoD contractors. NIST 800-171 compliant with CMMC Level 3 certification.",
        "country": "United States",
        "state": "CA"
    }
    
    # Score the company
    result = scoring_engine.calculate_company_score(test_company)
    
    print(f"\\nDETAILED SCORING BREAKDOWN FOR: {result.get('company_name', test_company['name'])}")
    print("-" * 60)
    print(f"Total Score: {result['total_score']:.1f}/100")
    print(f"Tier Classification: {result['tier_classification'].replace('_', ' ').title()}")
    
    print(f"\\nComponent Scores:")
    for component, score in result['component_scores'].items():
        print(f"  {component}: {score:.1f}/100")
    
    print(f"\\nKeywords Found:")
    for category, keywords in result['keywords_found'].items():
        if keywords:
            print(f"  {category}: {', '.join(keywords)}")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "individual":
        test_individual_company_scoring()
    else:
        test_scoring_engine_with_prospect_database()
