"""
Atomus TAM Research - Complete API Integration Test
This script demonstrates the full API integration workflow
"""

import json
from datetime import datetime
from pathlib import Path

from src.api_integrations import (
    create_hubspot_client,
    create_openai_client, 
    create_highergov_client
)
from src.utils import (
    get_logger,
    get_performance_tracker,
    log_system_info,
    log_system_shutdown
)


def test_complete_workflow():
    """
    Test the complete Atomus TAM Research workflow with all API integrations
    """
    logger = get_logger()
    tracker = get_performance_tracker()
    
    log_system_info()
    
    try:
        tracker.start_timing("complete_workflow_test")
        
        # Initialize all API clients
        logger.info("🚀 Initializing API clients...")
        
        hubspot_client = create_hubspot_client()
        openai_client = create_openai_client()
        highergov_client = create_highergov_client()
        
        # Test connections
        logger.info("🔗 Testing API connections...")
        
        hubspot_status = hubspot_client.test_connection()
        logger.info(f"✅ HubSpot: {hubspot_status['status']}")
        
        openai_status = openai_client.test_connection()
        logger.info(f"✅ OpenAI: {openai_status['status']} | Model: {openai_status['model']}")
        
        highergov_status = highergov_client.test_connection()
        logger.info(f"✅ HigherGov: {highergov_status['status']}")
        
        # Set up HubSpot properties (one-time setup)
        logger.info("🏗️ Setting up HubSpot custom properties...")
        try:
            properties_created = hubspot_client.setup_atomus_properties()
            logger.info(f"✅ Properties setup: {len(properties_created['companies'])} company properties, "
                       f"{len(properties_created['contacts'])} contact properties")
        except Exception as e:
            logger.warning(f"⚠️ Properties may already exist: {str(e)}")
        
        # Test with a subset of the 13 test companies
        test_companies = ["Firestorm", "Firehawk", "Overland AI"]
        
        logger.info(f"📋 Testing workflow with {len(test_companies)} companies: {test_companies}")
        
        workflow_results = []
        
        for company in test_companies:
            logger.info(f"🔍 Processing company: {company}")
            
            company_result = {
                "company_name": company,
                "timestamp": datetime.now().isoformat(),
                "workflow_steps": {}
            }
            
            # Step 1: HigherGov - Analyze defense contractor status
            logger.info(f"🛡️ Step 1: Analyzing defense contractor status for {company}")
            try:
                defense_analysis = highergov_client.analyze_defense_contractor_status(company)
                company_result["workflow_steps"]["defense_analysis"] = {
                    "status": "success",
                    "defense_score": defense_analysis["defense_contractor_score"],
                    "contract_count": defense_analysis["contract_analysis"]["defense_contracts"],
                    "identifiers": defense_analysis["identifiers"]
                }
                logger.info(f"✅ Defense analysis: Score {defense_analysis['defense_contractor_score']}")
            except Exception as e:
                logger.error(f"❌ Defense analysis failed: {str(e)}")
                company_result["workflow_steps"]["defense_analysis"] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            # Step 2: OpenAI - Conduct AI research
            logger.info(f"🤖 Step 2: Conducting AI research for {company}")
            try:
                ai_research = openai_client.conduct_research(
                    company_name=company,
                    research_type="basic_research",
                    research_category="company_overview"
                )
                company_result["workflow_steps"]["ai_research"] = {
                    "status": "success",
                    "tokens_used": ai_research["metadata"]["tokens_used"],
                    "research_summary": ai_research["content"][:200] + "..." if len(ai_research["content"]) > 200 else ai_research["content"]
                }
                logger.info(f"✅ AI research: {ai_research['metadata']['tokens_used']} tokens used")
            except Exception as e:
                logger.error(f"❌ AI research failed: {str(e)}")
                company_result["workflow_steps"]["ai_research"] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            # Step 3: Calculate combined score (simplified version)
            defense_score = company_result["workflow_steps"]["defense_analysis"].get("defense_score", 0) if company_result["workflow_steps"]["defense_analysis"]["status"] == "success" else 0
            
            # Simple scoring calculation (this would use the full scoring engine in production)
            combined_score = min(defense_score * 0.35 + 50, 100)  # Simplified calculation
            
            # Determine tier
            if combined_score >= 90:
                tier = "tier_1"
            elif combined_score >= 75:
                tier = "tier_2"
            elif combined_score >= 60:
                tier = "tier_3"
            elif combined_score >= 45:
                tier = "tier_4"
            else:
                tier = "excluded"
            
            company_result["calculated_score"] = round(combined_score, 1)
            company_result["tier_classification"] = tier
            
            # Step 4: HubSpot - Create/update company record
            logger.info(f"📊 Step 3: Creating HubSpot record for {company}")
            try:
                hubspot_data = {
                    "name": company,
                    "atomus_score": company_result["calculated_score"],
                    "defense_contract_score": defense_score,
                    "tier_classification": tier,
                    "last_research_date": datetime.now().strftime("%Y-%m-%d"),
                    "research_summary": company_result["workflow_steps"]["ai_research"].get("research_summary", "Research failed") if company_result["workflow_steps"]["ai_research"]["status"] == "success" else "Research failed"
                }
                
                # Search for existing company first
                existing_companies = hubspot_client.search_companies({"name": company})
                
                if existing_companies:
                    # Update existing company
                    company_id = existing_companies[0]["id"]
                    updated_company = hubspot_client.update_company(company_id, hubspot_data)
                    company_result["workflow_steps"]["hubspot_sync"] = {
                        "status": "updated",
                        "company_id": company_id
                    }
                    logger.info(f"✅ Updated HubSpot record: {company_id}")
                else:
                    # Create new company
                    new_company = hubspot_client.create_company(hubspot_data)
                    company_result["workflow_steps"]["hubspot_sync"] = {
                        "status": "created",
                        "company_id": new_company["id"]
                    }
                    logger.info(f"✅ Created HubSpot record: {new_company['id']}")
                    
            except Exception as e:
                logger.error(f"❌ HubSpot sync failed: {str(e)}")
                company_result["workflow_steps"]["hubspot_sync"] = {
                    "status": "failed",
                    "error": str(e)
                }
            
            workflow_results.append(company_result)
            logger.info(f"✅ Completed workflow for {company} | Score: {company_result['calculated_score']} | Tier: {tier}")
        
        # Save workflow results
        results_dir = Path("data/research_results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"complete_workflow_test_{timestamp}.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(workflow_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Workflow results saved: {results_file}")
        
        # Log final statistics
        logger.info("📊 WORKFLOW COMPLETION SUMMARY:")
        
        successful_companies = [r for r in workflow_results if all(
            step.get("status") in ["success", "created", "updated"] 
            for step in r["workflow_steps"].values()
        )]
        
        logger.info(f"   Companies processed: {len(workflow_results)}")
        logger.info(f"   Fully successful: {len(successful_companies)}")
        logger.info(f"   Average score: {sum(r['calculated_score'] for r in workflow_results) / len(workflow_results):.1f}")
        
        # Tier distribution
        tier_counts = {}
        for result in workflow_results:
            tier = result["tier_classification"]
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        logger.info(f"   Tier distribution: {tier_counts}")
        
        # API usage summary
        hubspot_client.log_stats_summary()
        openai_client.log_stats_summary()
        highergov_client.log_stats_summary()
        
        tracker.end_timing("complete_workflow_test", f"Processed {len(workflow_results)} companies")
        
        return workflow_results
        
    except Exception as e:
        logger.error(f"❌ Complete workflow test failed: {str(e)}")
        raise
    finally:
        log_system_shutdown()


def test_individual_apis():
    """
    Test each API individually for troubleshooting
    """
    logger = get_logger()
    
    logger.info("🔧 Testing individual API connections...")
    
    # Test HubSpot
    try:
        hubspot_client = create_hubspot_client()
        hubspot_status = hubspot_client.test_connection()
        logger.info(f"✅ HubSpot API: {hubspot_status}")
    except Exception as e:
        logger.error(f"❌ HubSpot API failed: {str(e)}")
    
    # Test OpenAI
    try:
        openai_client = create_openai_client()
        openai_status = openai_client.test_connection()
        logger.info(f"✅ OpenAI API: {openai_status}")
    except Exception as e:
        logger.error(f"❌ OpenAI API failed: {str(e)}")
    
    # Test HigherGov
    try:
        highergov_client = create_highergov_client()
        highergov_status = highergov_client.test_connection()
        logger.info(f"✅ HigherGov API: {highergov_status}")
    except Exception as e:
        logger.error(f"❌ HigherGov API failed: {str(e)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "individual":
        test_individual_apis()
    else:
        test_complete_workflow()
