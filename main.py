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
        
        # Save data
        if listings:
            # Determine output filenames
            if OUTPUT_FILENAME:
                json_file = f"output/{OUTPUT_FILENAME}.json"
                csv_file = f"output/{OUTPUT_FILENAME}.csv"
                excel_file = f"output/{OUTPUT_FILENAME}.xlsx"
            else:
                json_file = None
                csv_file = None
                excel_file = None
            
            # Export in requested format
            if EXPORT_FORMAT in ["json", "all"]:
                data_handler.save_json(listings, json_file)
            
            if EXPORT_FORMAT in ["csv", "all"]:
                data_handler.save_csv(listings, csv_file)
            
            if EXPORT_FORMAT in ["excel", "all"]:
                data_handler.export_to_excel(listings, excel_file)
            
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
