"""
Flask API server for Gumtree Scraper
Allows n8n.cloud to trigger the scraper via HTTP requests
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import traceback
from gumtree_scraper import GumtreeScraper
from data_handler import DataHandler
import json
import os
from datetime import datetime
import pytz

# Australian timezone
AUSTRALIA_TZ = pytz.timezone('Australia/Sydney')

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from n8n.cloud

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Gumtree Scraper API"}), 200

@app.route('/scrape', methods=['POST'])
def scrape():
    """
    Main scraping endpoint
    Accepts JSON with scraping parameters:
    {
        "category_url": "s-farming-veterinary/nsw/c21210l3008839",
        "max_pages": 1,
        "max_listings": 5,
        "location": "",
        "save_to_sheets": true
    }
    """
    try:
        # Get parameters from request (or use Railway environment variables as defaults)
        data = request.get_json() or {}
        
        # Use Railway environment variables as defaults, request body overrides them
        category_url = data.get('category_url') or os.environ.get("CATEGORY_URL", "s-farming-veterinary/nsw/c21210l3008839")
        max_pages = data.get('max_pages') if 'max_pages' in data else int(os.environ.get("MAX_PAGES", "1"))
        max_listings = data.get('max_listings') if 'max_listings' in data else (int(os.environ.get("MAX_LISTINGS", "24")) if os.environ.get("MAX_LISTINGS") else 24)
        location = data.get('location') or os.environ.get("LOCATION", "")
        save_to_sheets = data.get('save_to_sheets', True)  # API parameter only, not in env vars
        
        # Initialize scraper and data handler
        scraper = GumtreeScraper()
        data_handler = DataHandler()
        
        try:
            # Scrape category (this can take time)
            # Timeout set to 1200 seconds (20 minutes) to handle up to 24 listings
            # Each listing detail fetch takes ~3-5 seconds, so 24 listings = ~2-4 minutes minimum
            listings = scraper.scrape_category(
                category=category_url,
                location=location,
                max_pages=max_pages,
                max_listings=max_listings
            )
            
            # Get Australian time
            aus_time = datetime.now(AUSTRALIA_TZ)
            result = {
                "success": True,
                "listings_count": len(listings),
                "listings": listings,
                "scraped_at": aus_time.isoformat()
            }
            
            # Save data if listings found
            if listings:
                # Clear old output files
                data_handler._clear_output_files()
                
                # Save to Google Sheets if requested
                if save_to_sheets:
                    success = data_handler.save_to_google_sheets(listings)
                    result["google_sheets_saved"] = success
                    if not success:
                        result["warning"] = "Failed to save to Google Sheets. Saved to local files as backup."
                
                # Always save JSON locally
                data_handler.save_json(listings)
                
                # Get statistics
                stats = data_handler.get_statistics(listings)
                result["statistics"] = stats
                
                # Read the saved JSON file to include in response
                output_file = os.path.join(data_handler.output_dir, data_handler.data_file)
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        saved_data = json.load(f)
                        result["metadata"] = saved_data.get("metadata", {})
            else:
                result["message"] = "No listings found"
            
            # Log that scraping is complete
            print(f"✅ Scraping completed. Found {len(listings)} listings. Preparing response...")
            sys.stdout.flush()
            
            # Prepare response - don't include full metadata to reduce size
            # The listings are the important part
            response_data = {
                "success": True,
                "listings_count": len(listings),
                "listings": listings,
                "scraped_at": result["scraped_at"],
                "statistics": result.get("statistics", {})
            }
            
            print(f"✅ Response prepared. Returning to n8n...")
            sys.stdout.flush()
            
            return jsonify(response_data), 200
            
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            # Get Australian time
            aus_time = datetime.now(AUSTRALIA_TZ)
            return jsonify({
                "success": False,
                "error": error_msg,
                "traceback": error_trace,
                "scraped_at": aus_time.isoformat()
            }), 500
        finally:
            # Close scraper in background to not block response
            try:
                scraper.close()
            except:
                pass  # Don't block response if cleanup fails
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"API error: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500

@app.route('/scrape', methods=['GET'])
def scrape_get():
    """GET endpoint for simple scraping with query parameters"""
    try:
        category_url = request.args.get('category_url', 's-farming-veterinary/nsw/c21210l3008839')
        max_pages = int(request.args.get('max_pages', 1))
        max_listings = int(request.args.get('max_listings', 5))
        location = request.args.get('location', '')
        save_to_sheets = request.args.get('save_to_sheets', 'true').lower() == 'true'
        
        # Create a POST-like request internally
        data = {
            "category_url": category_url,
            "max_pages": max_pages,
            "max_listings": max_listings,
            "location": location,
            "save_to_sheets": save_to_sheets
        }
        
        # Temporarily set request.json
        original_json = request.json
        request.json = data
        
        try:
            return scrape()
        finally:
            request.json = original_json
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"API error: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500

if __name__ == '__main__':
    # Run the server
    port = int(os.environ.get('PORT', 5001))  # Changed to 5001 to avoid AirPlay conflict
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"Starting Gumtree Scraper API server on {host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"Scrape endpoint: http://{host}:{port}/scrape")
    
    app.run(host=host, port=port, debug=False)

