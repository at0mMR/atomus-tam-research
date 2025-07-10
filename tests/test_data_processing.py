"""
Atomus TAM Research - Data Processing Test
This script demonstrates the data processing capabilities with the prospect database
"""

import json
import sys
import os
import pandas as pd
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_processing import AtomDataProcessor
from utils import get_logger, log_system_info, log_system_shutdown, get_performance_tracker


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
        processor = AtomDataProcessor()
        
        # Load prospect database
        logger.info("📖 Loading prospect database...")
        df = processor.load_prospect_database()
        
        if not df:
            logger.error("❌ No data found in prospect database")
            return
        
        logger.info(f"✅ Loaded {len(df)} companies from prospect database")
        
        # Test data validation
        logger.info("🔍 Testing data validation...")
        validated_companies = []
        validation_results = []
        
        for company_data in df:
            validation_result_obj = processor.validate_company_data(company_data)
            is_valid = validation_result_obj['is_valid']
            errors = validation_result_obj['errors']
            
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
        if cleaned_companies:
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
        
        avg_quality = sum(score["quality_score"] for score in quality_scores) / len(quality_scores) if quality_scores else 0
        logger.info(f"✅ Data quality analysis complete | Average quality: {avg_quality:.1f}%")
        
        # Test saving processed data
        logger.info("💾 Testing data saving...")
        
        # Save processed data (the processor should handle this)
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S") if 'pd' in globals() else datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"../data/processed_prospect_database_{timestamp}.csv"
        
        try:
            # Save the data
            processor.save_processed_data(deduplicated_companies, output_file)
            logger.info(f"✅ Processed data saved: {output_file}")
        except Exception as e:
            logger.warning(f"⚠️ Could not save processed data: {str(e)}")
            output_file = "Not saved due to error"
        
        # Generate comprehensive test report
        test_report = {
            "test_summary": {
                "timestamp": pd.Timestamp.now().isoformat() if 'pd' in globals() else datetime.now().isoformat(),
                "total_companies_loaded": len(df),
                "companies_validated": valid_count,
                "validation_success_rate": f"{(valid_count / len(df) * 100):.1f}%" if len(df) > 0 else "0%",
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
            "top_quality_companies": sorted(quality_scores, key=lambda x: x["quality_score"], reverse=True)[:5] if quality_scores else [],
            "low_quality_companies": sorted(quality_scores, key=lambda x: x["quality_score"])[:3] if quality_scores else []
        }
        
        # Save test report
        report_file = Path(f"../data/research_results/data_processing_test_report_{timestamp}.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(test_report, f, indent=2)
        
        logger.info(f"📋 Test report saved: {report_file}")
        
        # Print summary to console
        print("\\n" + "="*60)
        print("DATA PROCESSING TEST SUMMARY")
        print("="*60)
        print(f"Companies loaded: {len(df)}")
        print(f"Companies validated: {valid_count} ({(valid_count / len(df) * 100):.1f}%)" if len(df) > 0 else "No companies loaded")
        print(f"Companies after deduplication: {len(deduplicated_companies)}")
        print(f"Duplicates removed: {duplicates_removed}")
        print(f"Average data quality: {avg_quality:.1f}%")
        print(f"Output file: {output_file}")
        print(f"Test report: {report_file}")
        
        # Show top quality companies
        if test_report["top_quality_companies"]:
            print(f"\\nTOP 5 QUALITY COMPANIES:")
            for i, company in enumerate(test_report["top_quality_companies"], 1):
                print(f"{i}. {company['company_name']}: {company['quality_score']:.1f}%")
        
        # Show validation issues
        failed_validations = [r for r in validation_results if not r["is_valid"]]
        if failed_validations:
            print(f"\\nVALIDATION ISSUES:")
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


def test_individual_data_operations():
    """
    Test individual data processing operations
    """
    logger = get_logger()
    logger.info("🧪 Testing individual data operations...")
    
    # Create data processor
    processor = AtomDataProcessor()
    
    # Test with a sample company
    sample_company = {
        "name": "Sample Defense Corp",
        "website": "https://sampledefense.com",
        "industry": "Defense Manufacturing",
        "description": "A defense manufacturing company specializing in advanced systems."
    }
    
    logger.info(f"✅ Sample company created: {sample_company['name']}")
    
    # Test validation
    validation_result = processor.validate_company_data(sample_company)
    logger.info(f"✅ Validation result: {validation_result['is_valid']} | Errors: {validation_result['errors']}")
    
    # Test data quality scoring
    quality_score = processor.calculate_data_quality_score(sample_company)
    logger.info(f"✅ Data quality score: {quality_score:.1f}%")
    
    # Test cleaning
    cleaned_data = processor.clean_and_normalize_data(sample_company)
    logger.info(f"✅ Data cleaned: {len(cleaned_data)} fields")
    
    return sample_company


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "individual":
        test_individual_data_operations()
    else:
        test_data_processing()
