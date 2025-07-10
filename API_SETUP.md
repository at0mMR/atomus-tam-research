# API Setup Instructions

## Setting Up Your API Credentials

To use the Atomus TAM Research system, you need to configure your API credentials:

### 1. Create Environment File

Copy the example environment file:
```bash
cp config/.env.example config/.env
```

### 2. Add Your API Credentials

Edit `config/.env` with your actual API keys (provided separately):

```bash
# HubSpot API Configuration
HUBSPOT_API_KEY=[your_hubspot_api_key]
HUBSPOT_PORTAL_ID=[your_portal_id_if_available]

# OpenAI API Configuration  
OPENAI_API_KEY=[your_openai_api_key]
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=2000

# HigherGov API Configuration (when available)
HIGHERGOV_API_KEY=[your_highergov_api_key]
HIGHERGOV_BASE_URL=https://api.highergov.com/v1
```

**Note**: The actual API keys have been provided separately in the project instructions. Replace the bracketed placeholders with the actual keys.

### 3. Test Your Setup

Run the test scripts to verify your API connections:

```python
# Test HubSpot connection
from src.api_integrations import create_hubspot_client
client = create_hubspot_client()
connection_info = client.test_connection()
print(f"HubSpot connected: {connection_info}")

# Test OpenAI connection  
from src.api_integrations import create_openai_client
ai_client = create_openai_client()
ai_connection = ai_client.test_connection()
print(f"OpenAI connected: {ai_connection}")
```

### 4. Set Up HubSpot Custom Properties

Run the property setup to create Atomus-specific fields:

```python
client = create_hubspot_client()
properties = client.setup_atomus_properties()
print(f"Created properties: {properties}")
```

## Quick Start Test

Test the system with one of the 13 test companies:

```python
from src.api_integrations import create_openai_client, create_hubspot_client

# Initialize clients
ai_client = create_openai_client()
hubspot_client = create_hubspot_client()

# Test OpenAI research
research_result = ai_client.conduct_research(
    company_name="Firestorm",
    research_type="basic_research", 
    research_category="company_overview"
)
print(f"Research completed: {research_result['company_name']}")

# Test HubSpot company creation
company_data = {
    "name": "Firestorm",
    "atomus_score": 78,
    "tier_classification": "tier_2",
    "research_summary": research_result['content'][:500]  # First 500 chars
}
company = hubspot_client.create_company(company_data)
print(f"Company created in HubSpot: {company['id']}")
```

## Security Notes

- The `config/.env` file is automatically ignored by Git (see .gitignore)
- Never commit API keys to version control
- Use environment variables in production environments
- Rotate API keys regularly for security

## Testing with All 13 Companies

Once basic setup is verified:

```python
# Test companies list
test_companies = [
    "Firestorm", "Firehawk", "Overland AI", "Kform", 
    "American Maglev Technologies", "Matsys", "H3X",
    "Compass Technologies Group", "Martian Sky", 
    "Orbital Composites", "Hybron Technologies", 
    "Image Insight", "Force Engineering"
]

# Conduct batch research (start with small batch)
results = ai_client.batch_research(test_companies[:3])  # Test with first 3
print(f"Research completed for {len(results)} companies")

# Save results
saved_path = ai_client.save_research_results(results)
print(f"Results saved to: {saved_path}")
```

## Current System Status

✅ **Completed (Steps 1-5)**:
- Repository foundation and structure
- Configuration files (scoring, prompts)
- Logging infrastructure 
- HubSpot API integration with custom properties
- OpenAI API integration with research automation

⏳ **Next Steps**:
- Step 6: HigherGov API integration
- Step 7: Data processing foundation
- Step 8: Scoring engine implementation
- Step 9: Web research automation
- Step 10: Testing infrastructure

## Troubleshooting

**Common Issues:**

1. **API Key Errors**: Ensure keys are correctly set in `config/.env`
2. **HubSpot Permission Errors**: Verify API key has proper scopes
3. **OpenAI Rate Limits**: The system includes automatic rate limiting
4. **Import Errors**: Make sure you're running from the project root directory

**Getting Help:**
- Check the logs in `data/logs/` for detailed error information
- All API calls and errors are automatically logged
- Use the built-in test functions to isolate issues
