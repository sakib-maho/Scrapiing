"""
Main execution script for Gumtree Scraping Automation
"""
import argparse
import sys
from gumtree_scraper import GumtreeScraper
from data_handler import DataHandler


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Gumtree Scraping Automation using Scrapfly API"
    )
    parser.add_argument(
        "--search",
        type=str,
        help="Search query for listings"
    )
    parser.add_argument(
        "--location",
        type=str,
        default="",
        help="Location filter (optional)"
    )
    parser.add_argument(
        "--category",
        type=str,
        help="Category to scrape (category name or URL path)"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Specific listing URL to scrape details"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="Maximum number of pages to scrape (default: 5)"
    )
    parser.add_argument(
        "--login",
        action="store_true",
        help="Attempt to login to Gumtree account"
    )
    parser.add_argument(
        "--export-format",
        type=str,
        choices=["json", "csv", "excel", "all"],
        default="all",
        help="Export format (default: all)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Custom output filename (without extension)"
    )
    
    args = parser.parse_args()
    
    # Initialize scraper and data handler
    scraper = GumtreeScraper()
    data_handler = DataHandler()
    
    try:
        # Login if requested
        if args.login:
            print("Attempting to login to Gumtree...")
            if scraper.login():
                print("Login successful!")
            else:
                print("Login failed. Continuing without login...")
        
        listings = []
        
        # Search listings
        if args.search:
            print(f"\nSearching for: '{args.search}'")
            if args.location:
                print(f"Location: {args.location}")
            listings = scraper.search_listings(
                query=args.search,
                location=args.location,
                max_pages=args.pages
            )
            print(f"Found {len(listings)} listings")
        
        # Scrape category
        elif args.category:
            print(f"\nScraping category: {args.category}")
            listings = scraper.scrape_category(
                category=args.category,
                location=args.location,
                max_pages=args.pages
            )
            print(f"Found {len(listings)} listings")
        
        # Get specific listing details
        elif args.url:
            print(f"\nScraping listing: {args.url}")
            details = scraper.get_listing_details(args.url)
            if details.get("success"):
                listings = [details]
                print("Listing details scraped successfully")
            else:
                print(f"Failed to scrape listing: {details.get('error')}")
                return 1
        
        else:
            print("No action specified. Use --search, --category, or --url")
            parser.print_help()
            return 1
        
        # Save data
        if listings:
            # Determine output filenames
            if args.output:
                json_file = f"output/{args.output}.json"
                csv_file = f"output/{args.output}.csv"
                excel_file = f"output/{args.output}.xlsx"
            else:
                json_file = None
                csv_file = None
                excel_file = None
            
            # Export in requested format
            if args.export_format in ["json", "all"]:
                data_handler.save_json(listings, json_file)
            
            if args.export_format in ["csv", "all"]:
                data_handler.save_csv(listings, csv_file)
            
            if args.export_format in ["excel", "all"]:
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
