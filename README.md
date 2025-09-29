# IBIC2025 Conference Web Scraper

**Author: Ming Liu**

## Overview
This web scraper is designed to extract all abstracts and papers from the IBIC2025 conference (https://meow.elettra.eu/90/index.html). The scraper creates folders organized by Session categories and downloads paper information and PDF files for each session.

## File Description
- `ibic2025_scraper.py` - Main scraper script with comprehensive features
- `ibic2025_analyze_results.py` - Results analysis and summary generator
- `requirements.txt` - Python dependencies list
- `README.md` - This documentation

## Requirements
- Python 3.7+
- Stable internet connection

## Installation

1. Ensure Python 3.7 or higher is installed
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Run the main scraper
```bash
python ibic2025_scraper.py
```

### Analyze results
```bash
python ibic2025_analyze_results.py
```

## Output Directory Structure

```
IBIC2025_Data/
├── Sessions/                    # Session-categorized paper data
│   ├── MOIG - Welcome/
│   │   ├── papers_data.json     # Detailed JSON data
│   │   ├── papers_data.csv      # CSV data (Excel compatible)
│   │   └── papers_summary.txt   # Human-readable text summary
│   ├── MOKG - Keynote/
│   └── ...
├── PDFs/                        # PDF files organized by session
│   ├── MOIG - Welcome/
│   │   ├── MOIG01 - Paper Title.pdf
│   │   └── ...
│   ├── MOKG - Keynote/
│   └── ...
├── IBIC2025_Complete_Index.json  # Master data index (JSON format)
├── IBIC2025_All_Papers.csv      # Complete papers CSV table
├── IBIC2025_Final_Report.txt    # Final scraping report
└── Debug/                        # Debug information and logs
```

## Features

### Data Extraction
- Paper IDs and titles
- Author information
- Institution details
- Paper abstracts
- PDF download links
- DOI information
- Received and accepted dates

### File Organization
- Automatic session-based folder creation
- PDF files renamed with paper titles
- Multiple output formats (JSON, CSV, TXT)

### Error Handling
- Network request retry mechanism
- Comprehensive logging
- Statistics tracking

## Configuration Options

You can modify the following configurations in the script:

```python
# Base URL
base_url = "https://meow.elettra.eu/90/"

# Output directory
output_dir = "IBIC2025_Data"

# Request delay (seconds)
delay_between_requests = 1-2

# Retry attempts
max_retries = 3
```

## Log Files
- `ibic2025_scraper.log` - Main scraper log

## Important Notes

1. **Network Stability**: Ensure stable internet connection, scraping process may take considerable time
2. **Storage Space**: Ensure sufficient disk space for PDF files
3. **Request Frequency**: Script includes appropriate delays to avoid server overload
4. **Filename Restrictions**: PDF filenames are automatically sanitized for compatibility

## FAQ

### Q: What if the scraping process is interrupted?
A: Re-run the script. Already downloaded files will be skipped, only new content will be downloaded.

### Q: Some PDF downloads fail?
A: Check the log files for detailed error information. Could be network issues or missing files.

### Q: How to scrape only specific sessions?
A: Modify the sessions_config list in the script to include only desired sessions.

### Q: Output data format doesn't meet requirements?
A: Modify the save functions to customize output formats.

## Technical Support

If you encounter issues, please check:
1. Python version meets requirements
2. All dependencies are correctly installed
3. Network connection is stable
4. Target website is accessible

## Disclaimer

This script is for academic research purposes only. Please comply with relevant website terms of use and copyright regulations. Users are responsible for any consequences arising from using this script.

## Version History

### v3.0 (Current)
- Complete English localization
- Author attribution (Ming Liu)
- Enhanced documentation
- Comprehensive error handling
- Multi-format data export

### v2.0 (Previous)
- Improved HTML parsing algorithms
- More accurate paper information extraction
- Multiple output format support
- Detailed statistics
- Enhanced logging

### v1.0 (Initial)
- Basic scraping functionality
- Session categorization
- PDF downloads
- JSON data output