# Atomus TAM Research & Scoring System

## Overview

GTM Intelligence Agent for Atomus, focused exclusively on defense contractors who require NIST 800-171 and CMMC compliance solutions. The system identifies, researches, scores, and prioritizes defense contractors based on their potential need for Atomus's cybersecurity compliance services.

## Project Structure

```
atomus-tam-research/
├── src/
│   ├── scoring_engine.py          # Core scoring algorithm implementation
│   ├── web_research.py            # Web scraping and research automation
│   ├── data_processing.py         # Data validation and transformation
│   ├── api_integrations/
│   │   ├── hubspot_client.py      # HubSpot API integration
│   │   ├── openai_client.py       # OpenAI API integration
│   │   └── highergov_client.py    # HigherGov API integration
│   └── utils/
│       ├── logging_config.py      # Centralized logging configuration
│       └── error_handling.py      # Error handling utilities
├── data/
│   ├── prospect_database.csv      # Main prospect database
│   ├── scoring_weights.json       # Scoring algorithm weights
│   ├── research_results/          # Research output storage
│   └── logs/                      # Application logs
├── config/
│   ├── .env.example              # Environment variables template
│   ├── scoring_config.yaml       # Scoring weights and keyword lists
│   └── research_prompts.yaml     # Research prompt templates
├── notebooks/
│   ├── mvp_demo.ipynb            # MVP demonstration notebook
│   ├── scoring_analysis.ipynb    # Scoring algorithm analysis
│   └── debugging_tools.ipynb     # Debugging and testing tools
├── tests/
│   └── test_scoring_engine.py    # Unit tests for scoring engine
├── requirements.txt               # Python dependencies
└── .gitignore                    # Git ignore rules
```

## Core Features

### Scoring Algorithm
- **Weighted Scoring System**: Defense Contract Score (35%) + Technology Relevance (30%) + Compliance Indicators (25%) + Firmographics (10%)
- **Keyword-Based Scoring**: Primary, Secondary, and Specialized keywords with different point values
- **Tier Classification**: 4-tier system (Tier 1: 90-100, Tier 2: 75-89, Tier 3: 60-74, Tier 4: 45-59)

### API Integrations
- **HubSpot**: CRM integration with custom properties
- **OpenAI**: AI-powered research and analysis
- **HigherGov**: Government contract data sourcing

### Research Capabilities
- High-volume basic research automation
- Configurable research prompts
- Web scraping with ethical practices
- Data validation and deduplication

## Test Dataset

Initial test companies for MVP validation:
- Firestorm
- Firehawk
- Overland AI
- Kform
- American Maglev Technologies
- Matsys
- H3X
- Compass Technologies Group
- Martian Sky
- Orbital Composites
- Hybron Technologies
- Image Insight
- Force Engineering

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/at0mMR/atomus-tam-research.git
   cd atomus-tam-research
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your API credentials
   ```

4. **Run the MVP demo**
   ```bash
   jupyter notebook notebooks/mvp_demo.ipynb
   ```

## Development Phases

### Phase 1: Foundation (Current)
- ✅ GitHub repository with proper structure
- ⏳ API connections with error handling
- ⏳ Logging system implementation
- ⏳ Configuration files setup
- ⏳ Scoring engine with test dataset

### Phase 2: Research & Enrichment
- ⏳ High-volume basic research capability
- ⏳ Modifiable prompt system
- ⏳ Web scraping with ethical practices
- ⏳ Data validation and deduplication

### Phase 3: HubSpot Integration
- ⏳ Export existing HubSpot data
- ⏳ Create new custom properties
- ⏳ Build sync functionality
- ⏳ Implement automated updates

## Success Metrics

- Successfully score and tier the 13 test companies
- Complete deep research on 2-3 companies
- Sync results to new HubSpot structure
- Demonstrate easy modification of research prompts
- Show clear ICP identification in HubSpot

## Compliance & Ethics

- Respect robots.txt and rate limiting
- Use rotational proxies for ethical scraping
- Maintain GDPR/CCPA compliance
- Follow CAN-SPAM regulations
- Implement proper API rate limiting

## Contributing

This project follows a modular development approach:
- Each function should be independently testable
- Detailed logging for every API call and scoring decision
- Configuration-driven design (no hardcoded values)
- Interactive testing via Jupyter notebooks
- Clear, actionable error messages

## License

Proprietary - Atomus Internal Use Only