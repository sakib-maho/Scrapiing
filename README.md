# Gumtree Scraping Automation

A comprehensive web scraping automation tool for Gumtree using Scrapfly API. This tool allows you to search listings, scrape categories, and extract detailed listing information.

## Features

- **Scrapfly API Integration**: Uses Scrapfly's anti-scraping protection and premium proxies
- **Search Functionality**: Search for listings by query and location
- **Category Scraping**: Scrape entire categories with pagination support
- **Detailed Listing Extraction**: Get comprehensive information from individual listings
- **Multiple Export Formats**: Export data as JSON, CSV, or Excel
- **Data Statistics**: Get insights about scraped data
- **Error Handling**: Robust error handling and retry mechanisms

## Prerequisites

- Python 3.8 or higher
- Scrapfly API key (already configured)
- Gumtree account credentials (already configured)

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The configuration is already set up in `config.py` with:
- Scrapfly API Key: `Scp-live-d51b8ee5150e481bba52f3fba8b8cbcd`
- Gumtree Email: `pepeandamino@gmail.com`
- Gumtree Password: `-trust555-`

You can modify these settings in `config.py` if needed.

## Usage

### Command Line Interface

#### Search for Listings
```bash
python main.py --search "laptop" --location "London" --pages 5
```

#### Scrape a Category
```bash
python main.py --category "computers" --pages 10
```

#### Get Specific Listing Details
```bash
python main.py --url "https://www.gumtree.com/p/..."
```

#### Login to Gumtree (Optional)
```bash
python main.py --search "bike" --login
```

#### Export Options
```bash
# Export as JSON only
python main.py --search "car" --export-format json

# Export as CSV only
python main.py --search "car" --export-format csv

# Export as Excel only
python main.py --search "car" --export-format excel

# Export in all formats (default)
python main.py --search "car" --export-format all
```

#### Custom Output Filename
```bash
python main.py --search "furniture" --output "furniture_listings"
```

### Python API

You can also use the scraper programmatically:

```python
from gumtree_scraper import GumtreeScraper
from data_handler import DataHandler

# Initialize
scraper = GumtreeScraper()
data_handler = DataHandler()

# Search listings
listings = scraper.search_listings(
    query="laptop",
    location="London",
    max_pages=5
)

# Save data
data_handler.save_json(listings)
data_handler.save_csv(listings)

# Get statistics
stats = data_handler.get_statistics(listings)
print(stats)

# Clean up
scraper.close()
```

## Output

Data is saved in the `output/` directory:
- `gumtree_data.json` - JSON format with metadata
- `gumtree_data.csv` - CSV format for spreadsheet applications
- `gumtree_data_[timestamp].xlsx` - Excel format with timestamps

## Data Structure

Each listing contains:
- `title`: Listing title
- `url`: Full URL to the listing
- `price`: Price (if available)
- `location`: Location (if available)
- `description`: Description snippet
- `images`: List of image URLs
- `seller`: Seller information
- `attributes`: Additional attributes (category, condition, etc.)
- `scraped_at`: Timestamp of when the data was scraped

## Project Structure

```
.
├── config.py              # Configuration settings
├── scrapfly_client.py     # Scrapfly API client
├── gumtree_scraper.py    # Main scraper class
├── data_handler.py       # Data export and handling
├── main.py               # Command-line interface
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── output/               # Output directory (created automatically)
```

## Scrapfly API Features

This tool leverages Scrapfly's advanced features:
- **JavaScript Rendering**: Handles dynamic content
- **Premium Proxies**: High-quality residential proxies
- **Anti-Scraping Protection**: Bypasses common anti-bot measures
- **Country Targeting**: Configured for UK (GB)

## Error Handling

The scraper includes:
- Automatic retries for failed requests
- Rate limiting to avoid being blocked
- Comprehensive error logging
- Graceful handling of missing data

## Limitations

1. **Login Functionality**: Full login may require additional implementation with Selenium for complex authentication flows
2. **Dynamic Content**: Some content may require JavaScript rendering (handled by Scrapfly)
3. **Rate Limits**: Be mindful of Scrapfly API rate limits and Gumtree's terms of service

## Best Practices

1. **Respect Rate Limits**: The scraper includes delays between requests
2. **Use Appropriate Pages**: Don't scrape excessive pages unnecessarily
3. **Check Terms of Service**: Ensure your usage complies with Gumtree's ToS
4. **Monitor API Usage**: Keep track of your Scrapfly API usage

## Troubleshooting

### No listings found
- Check if the search query or category is correct
- Verify that listings exist for your search criteria
- Check network connectivity and API key validity

### Login fails
- Verify credentials in `config.py`
- Some login flows may require Selenium for full automation
- Check if Gumtree has changed their login process

### API errors
- Verify Scrapfly API key is valid
- Check your Scrapfly account balance
- Review Scrapfly API documentation for any changes

## Support

For issues or questions:
1. Check the error messages in the console
2. Review Scrapfly API documentation
3. Verify configuration settings

## License

This project is provided as-is for educational and research purposes. Ensure compliance with Gumtree's Terms of Service and applicable laws when using this tool.
