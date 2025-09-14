# Finkraft

## Google Drive Demo Link : https://drive.google.com/file/d/1Dbbb147Z8NRSLcSjwftt9f_C7yiXJCd0/view?usp=sharing

**Smart CSV Data Processing & Validation Tool**

Transform messy CSV files into clean, standardized data with AI-powered intelligence.

## 🚀 What It Does

Finkraft automatically cleans and validates your CSV data through a simple 4-step process:

1. **Upload** - Drop your CSV file
2. **Map** - AI matches your headers to standard schema
3. **Fix** - Automated data quality fixes with AI suggestions
4. **Review** - Download clean, validated data

## ✨ Key Features

- **🤖 AI-Powered Mapping** - Intelligent header matching using Gemini AI
- **⚙️ Smart Data Fixes** - Automatic fixes for dates, emails, numbers, currencies
- **🔍 Quality Validation** - Comprehensive error detection and reporting  
- **📊 Progress Tracking** - Real-time validation metrics and fix summaries
- **💾 Clean Export** - Download standardized CSV with canonical column names

## 🛠️ Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment (optional - for AI features)
export USE_GEMINI=true
export GEMINI_API_KEY=your_api_key

# Run the app
streamlit run app.py
```

## 📋 Supported Data Types

- **Dates** - Auto-converts to YYYY-MM-DD format
- **Emails** - Validates and fixes common formatting issues
- **Phone Numbers** - Standardizes contact information
- **Currencies** - Handles symbols and conversions
- **Percentages** - Converts to decimal format (0-1)
- **Addresses** - Validates billing/shipping fields

## 🎯 Perfect For

- Data analysts cleaning messy datasets
- E-commerce order processing
- Customer data standardization
- Financial data validation
- Any CSV transformation workflow

## 🔧 Configuration

Key environment variables:
- `USE_GEMINI` - Enable AI features (default: false)
- `GEMINI_API_KEY` - Your Gemini API key
- `MISSING_DATA_THRESHOLD` - Max missing data % (default: 10.0)
- `COLUMN_UNMATCH_THRESHOLD` - Unmapped columns warning (default: 5)

## 📈 Data Quality Features

- **Deterministic Fixes** - Rule-based corrections for common issues
- **AI Suggestions** - Smart fixes for complex validation errors
- **Bulk Operations** - Apply fixes individually or in groups
- **Quality Metrics** - Track improvement percentages and fix types
- **Error Grouping** - Organized by error type for efficient review

---

**Built with Streamlit • Powered by Gemini AI • Made for Data Teams**
