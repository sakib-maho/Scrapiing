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
        # Get parameters from request
        data = request.get_json() or {}
        
        category_url = data.get('category_url', 's-farming-veterinary/nsw/c21210l3008839')
        max_pages = data.get('max_pages', 1)
        max_listings = data.get('max_listings', 5)
        location = data.get('location', '')
        save_to_sheets = data.get('save_to_sheets', True)
        
        # Initialize scraper and data handler
        scraper = GumtreeScraper()
        data_handler = DataHandler()
        
        try:
            # Scrape category
            listings = scraper.scrape_category(
                category=category_url,
                location=location,
                max_pages=max_pages,
                max_listings=max_listings
            )
            
            result = {
                "success": True,
                "listings_count": len(listings),
                "listings": listings,
                "scraped_at": datetime.now().isoformat()
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
            
            return jsonify(result), 200
            
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            return jsonify({
                "success": False,
                "error": error_msg,
                "traceback": error_trace,
                "scraped_at": datetime.now().isoformat()
            }), 500
        finally:
            scraper.close()
            
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

