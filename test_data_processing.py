"""
Atomus TAM Research - Data Processing Test
This script demonstrates the data processing capabilities with the prospect database
"""

import json
import pandas as pd
from pathlib import Path

from src import create_data_processor, CompanyData
from src.utils import get_logger, log_system_info, log_system_shutdown, get_performance_tracker


def test_data_processing():
    """
    Test the complete data processing workflow with the prospect database
    """
    logger = get_logger()
    tracker = get_performance_tracker()
    
    log_system_info()
    
    try:
        tracker.start_timing("data_processing_test")
        
        # Initialize data processor
        logger.info("🚀 Initializing data processor...")
        processor = create_data_processor()
        
        # Load prospect database
        logger.info("📖 Loading prospect database...")
        df = processor.load_prospect_database()
        
        if df.empty:
            logger.error("❌ No data found in prospect database")
            return
        
        logger.info(f"✅ Loaded {len(df)} companies from prospect database")
        
        # Test data validation
        logger.info("🔍 Testing data validation...")
        validated_companies = []
        validation_results = []
        
        for index, row in df.iterrows():
            company_data = row.to_dict()
            is_valid, errors = processor.validate_company_data(company_data)
            
            validation_result = {
                "company_name": company_data.get("name", "Unknown"),
                "is_valid": is_valid,
                "errors": errors,
                "data_quality_score": processor.calculate_data_quality_score(company_data)
            }
            validation_results.append(validation_result)
            
            if is_valid:
                validated_companies.append(company_data)
        
        valid_count = len(validated_companies)
        logger.info(f"✅ Validation complete | Valid: {valid_count}/{len(df)} | "
                   f"Rejection rate: {((len(df) - valid_count) / len(df) * 100):.1f}%")
        
        # Test data cleaning and normalization
        logger.info("🧹 Testing data cleaning and normalization...")
        cleaned_companies = []
        
        for company_data in validated_companies:
            cleaned_data = processor.clean_and_normalize_data(company_data)
            cleaned_companies.append(cleaned_data)
        
        logger.info(f"✅ Data cleaning complete | {len(cleaned_companies)} companies processed")
        
        # Test deduplication
        logger.info("🔄 Testing deduplication...")
        
        # Add a duplicate for testing
        test_duplicate = cleaned_companies[0].copy()
        test_duplicate["name"] = cleaned_companies[0]["name"] + " Inc."  # Slight variation
        cleaned_companies.append(test_duplicate)
        
        deduplicated_companies = processor.deduplicate_companies(cleaned_companies)
        duplicates_removed = len(cleaned_companies) - len(deduplicated_companies)
        
        logger.info(f"✅ Deduplication complete | Original: {len(cleaned_companies)} | "
                   f"Final: {len(deduplicated_companies)} | Duplicates removed: {duplicates_removed}")
        
        # Test API data processing simulation
        logger.info("🔗 Testing API data processing...")
        
        # Simulate HubSpot data
        hubspot_sample = {
            "id": "12345678",
            "properties": {
                "name": "Test Company",
                "domain": "testcompany.com",
                "industry": "Technology",
                "numberofemployees": "150",
                "annualrevenue": "5000000",
                "atomus_score": "78.5"
            }
        }
        
        processed_hubspot = processor.process_api_data(hubspot_sample, "hubspot")
        logger.info(f"✅ HubSpot data processed: {processed_hubspot.get('name')}")
        
        # Simulate HigherGov data
        highergov_sample = {
            "company_name": "Defense Corp",
            "defense_contractor_score": 85.2,
            "identifiers": {
                "cage_code": "1A234",
                "duns_number": "123456789"
            },
            "contract_analysis": {
                "total_contracts": 15,
                "defense_contracts": 12
            }
        }
        
        processed_highergov = processor.process_api_data(highergov_sample, "highergov")
        logger.info(f"✅ HigherGov data processed: {processed_highergov.get('name')}")
        
        # Test data quality scoring
        logger.info("📊 Testing data quality scoring...")
        quality_scores = []
        
        for company in deduplicated_companies:
            quality_score = processor.calculate_data_quality_score(company)
            quality_scores.append({
                "company_name": company.get("name"),
                "quality_score": quality_score
            })
        
        avg_quality = sum(score["quality_score"] for score in quality_scores) / len(quality_scores)
        logger.info(f"✅ Data quality analysis complete | Average quality: {avg_quality:.1f}%")
        
        # Test saving processed data
        logger.info("💾 Testing data saving...")
        
        # Create updated DataFrame with processed data
        processed_df = pd.DataFrame(deduplicated_companies)
        
        # Save to new file with timestamp
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"data/processed_prospect_database_{timestamp}.csv"
        saved_path = processor.save_prospect_database(processed_df, output_file)
        
        logger.info(f"✅ Processed data saved: {saved_path}")
        
        # Generate comprehensive test report
        test_report = {
            "test_summary": {
                "timestamp": pd.Timestamp.now().isoformat(),
                "total_companies_loaded": len(df),
                "companies_validated": valid_count,
                "validation_success_rate": f"{(valid_count / len(df) * 100):.1f}%",
                "companies_after_dedup": len(deduplicated_companies),
                "duplicates_removed": duplicates_removed,
                "average_data_quality": f"{avg_quality:.1f}%"
            },
            "validation_results": validation_results,
            "quality_scores": quality_scores,
            "sample_processed_data": {
                "hubspot_sample": processed_hubspot,
                "highergov_sample": processed_highergov
            },
            "top_quality_companies": sorted(quality_scores, key=lambda x: x["quality_score"], reverse=True)[:5],
            "low_quality_companies": sorted(quality_scores, key=lambda x: x["quality_score"])[:3]
        }
        
        # Save test report
        report_file = Path(f"data/research_results/data_processing_test_report_{timestamp}.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(test_report, f, indent=2)
        
        logger.info(f"📋 Test report saved: {report_file}")
        
        # Log processing statistics
        processor.log_stats_summary()
        
        # Print summary to console
        print("\n" + "="*60)
        print("DATA PROCESSING TEST SUMMARY")
        print("="*60)
        print(f"Companies loaded: {len(df)}")
        print(f"Companies validated: {valid_count} ({(valid_count / len(df) * 100):.1f}%)")
        print(f"Companies after deduplication: {len(deduplicated_companies)}")
        print(f"Duplicates removed: {duplicates_removed}")
        print(f"Average data quality: {avg_quality:.1f}%")
        print(f"Output file: {saved_path}")
        print(f"Test report: {report_file}")
        
        # Show top quality companies
        print(f"\nTOP 5 QUALITY COMPANIES:")
        for i, company in enumerate(test_report["top_quality_companies"], 1):
            print(f"{i}. {company['company_name']}: {company['quality_score']:.1f}%")
        
        # Show validation issues
        failed_validations = [r for r in validation_results if not r["is_valid"]]
        if failed_validations:
            print(f"\nVALIDATION ISSUES:")
            for result in failed_validations:
                print(f"• {result['company_name']}: {'; '.join(result['errors'])}")
        
        print("="*60)
        
        tracker.end_timing("data_processing_test", f"Processed {len(df)} companies")
        
        return test_report
        
    except Exception as e:
        logger.error(f"❌ Data processing test failed: {str(e)}")
        raise
    finally:
        log_system_shutdown()


def test_company_data_class():
    """
    Test the CompanyData dataclass functionality
    """
    logger = get_logger()
    logger.info("🧪 Testing CompanyData class...")
    
    # Create a sample company
    company = CompanyData(
        name="Sample Defense Corp",
        website="https://sampledefense.com",
        industry="Defense Manufacturing",
        employee_count=250,
        annual_revenue=30000000,
        atomus_score=85.5,
        tier_classification="tier_2"
    )
    
    logger.info(f"✅ CompanyData created: {company.name}")
    
    # Test conversion to dict
    company_dict = company.__dict__
    logger.info(f"✅ Converted to dict with {len(company_dict)} fields")
    
    # Test data processor with CompanyData object
    processor = create_data_processor()
    is_valid, errors = processor.validate_company_data(company)
    
    logger.info(f"✅ CompanyData validation: {is_valid} | Errors: {errors}")
    
    return company


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "class":
        test_company_data_class()
    else:
        test_data_processing()
