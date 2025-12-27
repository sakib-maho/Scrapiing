"""
Main execution script for Gumtree Scraping Automation
"""
import sys
from gumtree_scraper import GumtreeScraper
from data_handler import DataHandler

# Hardcoded configuration
CATEGORY_URL = "s-farming-veterinary/nsw/c21210l3008839"
MAX_PAGES = 1
MAX_LISTINGS = 1  # Maximum number of listings to scrape (None = scrape all)
LOCATION = ""  # Optional location filter
EXPORT_FORMAT = "all"  # Options: "json", "csv", "excel", "all"
OUTPUT_FILENAME = None  # None = use default, or specify custom name without extension


def main():
    """Main execution function"""
    # Initialize scraper and data handler
    scraper = GumtreeScraper()
    data_handler = DataHandler()
    
    try:
        print(f"\nScraping category: {CATEGORY_URL}")
        print(f"Max pages: {MAX_PAGES}")
        if MAX_LISTINGS:
            print(f"Max listings: {MAX_LISTINGS}")
        if LOCATION:
            print(f"Location filter: {LOCATION}")
        print()
        
        # Scrape category with hardcoded settings
        listings = scraper.scrape_category(
            category=CATEGORY_URL,
            location=LOCATION,
            max_pages=MAX_PAGES,
            max_listings=MAX_LISTINGS
        )
        
        print(f"\nFound {len(listings)} listings")
        
        # Save data to Google Sheets
        if listings:
            # Save to Google Sheets (appends only new data)
            success = data_handler.save_to_google_sheets(listings)
            if not success:
                print("Warning: Failed to save to Google Sheets. Saving to local files as backup...")
            
            # Always save JSON locally for n8n workflow compatibility
            data_handler.save_json(listings)
            
            # Print statistics
            stats = data_handler.get_statistics(listings)
            print("\n" + "="*50)
            print("Scraping Statistics:")
            print("="*50)
            for key, value in stats.items():
                if isinstance(value, dict):
                    print(f"{key}:")
                    for k, v in value.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"{key}: {value}")
            print("="*50)
        else:
            print("No listings found")
            return 1
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
        return 1
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        scraper.close()


if __name__ == "__main__":
    sys.exit(main())
