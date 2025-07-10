# Atomus TAM Research - Notebook Setup Guide

This guide will help you set up and use the interactive analysis notebooks for debugging and exploring the Atomus TAM Research system.

## 📚 Available Notebooks

### 1. `debugging_tools.ipynb` 
**Purpose**: Interactive API testing and troubleshooting
- Individual API connection testing (HubSpot, OpenAI, HigherGov)
- Environment variable validation
- Configuration file exploration
- End-to-end workflow testing
- Performance monitoring
- Custom testing area for debugging

### 2. `mvp_demo.ipynb`
**Purpose**: Complete workflow demonstration
- Full pipeline testing with sample companies
- Results analysis and visualization
- Performance metrics tracking
- Batch processing capabilities
- Export functionality

### 3. `scoring_analysis.ipynb`
**Purpose**: Scoring algorithm analysis and optimization
- Score distribution analysis
- Keyword effectiveness tracking
- Weight sensitivity analysis
- Tier optimization
- Company deep-dive analysis
- Configuration testing tools

## 🚀 Quick Setup

### Prerequisites
```bash
# Ensure you have Python 3.8+ and pip installed
python --version
pip --version
```

### 1. Install Dependencies
```bash
# From the project root directory
pip install -r requirements.txt

# Additional notebook-specific packages
pip install jupyter matplotlib seaborn plotly
```

### 2. Configure Environment Variables
```bash
# Copy the example environment file
cp config/.env.example config/.env

# Edit config/.env and add your API keys:
# HUBSPOT_API_KEY=na2-c562-6153-4837-bf92-c9abc4cc7ef7
# OPENAI_API_KEY=sk-proj-Hb07p0th8QM74Og-6E83sd4VfTnfdWqIvr...
# HIGHERGOV_API_KEY=[Your HigherGov API Key]
```

### 3. Start Jupyter
```bash
# Navigate to the project root
cd atomus-tam-research

# Start Jupyter server
jupyter notebook

# Or use Jupyter Lab for a more modern interface
jupyter lab
```

### 4. Open Notebooks
Navigate to the `notebooks/` directory in Jupyter and open any notebook to begin.

## 🔧 First-Time Testing Workflow

### Step 1: API Validation
1. Open `debugging_tools.ipynb`
2. Run the **System Information** section
3. Run the **Individual API Testing** sections
4. Verify all APIs are working correctly

### Step 2: Basic Workflow Test
1. Open `mvp_demo.ipynb`
2. Run the **System Initialization** section
3. Execute the **Process Sample Companies** section
4. Review results and performance metrics

### Step 3: Scoring Analysis
1. Open `scoring_analysis.ipynb`
2. Load and score test companies
3. Analyze score distributions and keyword effectiveness
4. Experiment with different weight configurations

## 🐛 Troubleshooting Common Issues

### Issue: Import Errors
```python
# If you see import errors, ensure the notebook can find the src directory
import sys
sys.path.append('../src')  # This should be in each notebook
```

### Issue: API Connection Failures
1. Verify your `.env` file has the correct API keys
2. Check that the keys are not expired
3. Test individual APIs in `debugging_tools.ipynb`

### Issue: Data Loading Problems
1. Ensure `data/prospect_database.csv` exists
2. Check file permissions
3. Run the data validation in `debugging_tools.ipynb`

### Issue: Module Not Found
```bash
# Install missing packages
pip install [missing-package-name]

# Common missing packages:
pip install pandas numpy matplotlib seaborn plotly
```

## 📊 Understanding the Output

### API Test Results
- ✅ = Successful connection
- ❌ = Failed connection (check API keys)
- ⚠️ = Warning (may still work)

### Scoring Results
- **Tier 1 (90-100)**: Immediate outreach priority
- **Tier 2 (75-89)**: High-value prospects
- **Tier 3 (60-74)**: Qualified prospects
- **Tier 4 (45-59)**: Nurture candidates
- **Excluded (<45)**: Low priority

### Performance Metrics
- **API Calls**: Number of requests made
- **Tokens Used**: OpenAI token consumption
- **Response Times**: Average API response times
- **Success Rates**: Percentage of successful operations

## 🎯 Best Practices

### 1. Start Small
- Test with 1-3 companies first
- Verify everything works before scaling up
- Use the individual API tests to isolate issues

### 2. Monitor API Usage
- Keep track of OpenAI token usage
- Respect API rate limits
- Use the performance monitoring sections

### 3. Save Your Work
- Export results from each notebook
- Save configuration changes to separate files
- Document any issues you discover

### 4. Iterative Testing
- Make small configuration changes
- Test immediately after changes
- Compare results with previous runs

## 🔄 Development Workflow

### Finding Issues
1. Use `debugging_tools.ipynb` for systematic testing
2. Check each API individually
3. Validate data quality and configuration
4. Test scoring algorithms with known data

### Making Changes
1. Modify configuration files in `config/`
2. Test changes in notebooks immediately
3. Compare before/after results
4. Document significant findings

### Scaling Up
1. Start with 3 companies
2. Increase to 5-10 companies
3. Process all 13 test companies
4. Monitor for any performance issues

## 📁 Generated Files

The notebooks will create several output files in `data/research_results/`:

- **Detailed Results**: `mvp_demo_detailed_YYYYMMDD_HHMMSS.json`
- **Summary CSV**: `mvp_demo_summary_YYYYMMDD_HHMMSS.csv`
- **Performance Data**: `mvp_demo_performance_YYYYMMDD_HHMMSS.json`
- **Scoring Analysis**: `scoring_analysis_YYYYMMDD_HHMMSS.csv`
- **Weight Analysis**: `weight_analysis_YYYYMMDD_HHMMSS.json`

## 🔗 Alternative Testing Methods

### Command Line Testing
```bash
# Run integration tests from command line
cd tests/
python test_complete_integration.py

# Run individual API tests
python test_complete_integration.py individual

# Run scoring engine tests
python test_scoring_engine.py

# Run data processing tests
python test_data_processing.py
```

### Quick API Checks
```bash
# Test specific functionality without notebooks
python -c "from src.api_integrations import create_hubspot_client; print(create_hubspot_client().test_connection())"
```

## 📞 Getting Help

### Common Solutions
1. **API Issues**: Check the API documentation and your key permissions
2. **Data Issues**: Validate your CSV files and data format
3. **Import Issues**: Ensure all dependencies are installed
4. **Performance Issues**: Monitor API rate limits and system resources

### Debugging Steps
1. Start with `debugging_tools.ipynb`
2. Test one component at a time
3. Check logs in `data/logs/`
4. Review configuration files in `config/`

---

**Ready to start testing!** 🚀 

Open `debugging_tools.ipynb` first to validate your setup, then proceed to `mvp_demo.ipynb` for the full workflow demonstration.