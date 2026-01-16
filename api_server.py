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
import threading
import time
import uuid
import requests

# Australian timezone
AUSTRALIA_TZ = pytz.timezone('Australia/Sydney')

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from n8n.cloud

def _normalize_location(raw_location):
    if raw_location is None or raw_location == "None" or raw_location == "null":
        return ""
    location = str(raw_location).strip().strip('"').strip("'")
    if not location or location.lower() == "none":
        return ""
    return location

def _parse_scrape_params(data):
    # Use Railway environment variables as defaults, request body overrides them
    category_url = data.get('category_url') or os.environ.get("CATEGORY_URL", "s-farming-veterinary/nsw/c21210l3008839")
    max_pages = data.get('max_pages') if 'max_pages' in data else int(os.environ.get("MAX_PAGES", "1"))

    # Handle max_listings: if max_pages > 1 and max_listings not explicitly set, use None (scrape all)
    if 'max_listings' in data:
        max_listings = data.get('max_listings')
        if max_listings is not None and max_listings != "":
            max_listings = int(max_listings)
        else:
            max_listings = None
    else:
        if max_pages > 1:
            max_listings = None
        else:
            max_listings = int(os.environ.get("MAX_LISTINGS", "24")) if os.environ.get("MAX_LISTINGS") else 24

    location = _normalize_location(data.get('location') or os.environ.get("LOCATION", ""))
    save_to_sheets = data.get('save_to_sheets', True)

    return {
        "category_url": category_url,
        "max_pages": max_pages,
        "max_listings": max_listings,
        "location": location,
        "save_to_sheets": save_to_sheets
    }

def _build_result_url(output_path):
    base_url = os.environ.get("N8N_RESULT_BASE_URL")
    if not base_url:
        return None
    base_url = base_url.rstrip("/")
    filename = os.path.basename(output_path)
    return f"{base_url}/{filename}"

def _post_callback(payload):
    callback_url = os.environ.get("N8N_CALLBACK_URL")
    if not callback_url:
        print("⚠️ N8N_CALLBACK_URL is not set; skipping callback.")
        return
    headers = {
        "Connection": "close",
        "Accept-Encoding": "identity"
    }
    try:
        response = requests.post(callback_url, json=payload, timeout=30, headers=headers)
        print(f"✅ Callback sent. Status={response.status_code}")
    except Exception as exc:
        print(f"❌ Failed to send callback: {exc}")

def run_job_and_callback(job_id, params):
    start_time = time.time()
    print(f"🚀 Job started. jobId={job_id}")
    sys.stdout.flush()

    scraper = GumtreeScraper()
    data_handler = DataHandler()
    secret = os.environ.get("N8N_WEBHOOK_SECRET", "")

    try:
        listings = scraper.scrape_category(
            category=params["category_url"],
            location=params["location"],
            max_pages=params["max_pages"],
            max_listings=params["max_listings"]
        )

        aus_time = datetime.now(AUSTRALIA_TZ)
        result = {
            "success": True,
            "listings_count": len(listings),
            "listings": listings,
            "scraped_at": aus_time.isoformat()
        }

        if listings:
            data_handler._clear_output_files()

            if params["save_to_sheets"]:
                success = data_handler.save_to_google_sheets(listings)
                result["google_sheets_saved"] = success
                if not success:
                    result["warning"] = "Failed to save to Google Sheets. Saved to local files as backup."

            data_handler.save_json(listings)
            result["statistics"] = data_handler.get_statistics(listings)

        payload = {
            "success": True,
            "jobId": job_id,
            "secret": secret
        }

        # Keep output format stable but surface scraping failures clearly for n8n
        scrape_error = getattr(scraper, "last_scrape_error", None)
        if scrape_error and not listings:
            payload["scrapeSuccess"] = False
            payload["error"] = scrape_error.get("error")
            payload["scrapeError"] = scrape_error
        else:
            payload["scrapeSuccess"] = True

        listings_json = json.dumps(listings, ensure_ascii=True)
        max_bytes = int(os.environ.get("N8N_MAX_CALLBACK_BYTES", "4000000"))
        if len(listings_json.encode("utf-8")) > max_bytes:
            output_file = os.path.join(data_handler.output_dir, data_handler.data_file)
            result_url = _build_result_url(output_file)
            if result_url:
                payload["resultUrl"] = result_url
                print(f"📦 Payload too large; sending resultUrl={result_url}")
            else:
                payload["listings"] = listings
                print("⚠️ Payload too large but N8N_RESULT_BASE_URL not set; sending listings inline.")
        else:
            payload["listings"] = listings

        _post_callback(payload)

    except Exception as exc:
        error_trace = traceback.format_exc()
        payload = {
            "success": False,
            "jobId": job_id,
            "error": str(exc),
            "traceback": error_trace,
            "secret": secret
        }
        _post_callback(payload)
    finally:
        try:
            scraper.close()
        except Exception:
            pass
        elapsed = time.time() - start_time
        print(f"✅ Job finished. jobId={job_id} duration={elapsed:.2f}s")
        sys.stdout.flush()

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
        data = request.get_json() or {}
        params = _parse_scrape_params(data)
        job_id = str(uuid.uuid4())

        thread = threading.Thread(
            target=run_job_and_callback,
            args=(job_id, params),
            daemon=True
        )
        thread.start()

        return jsonify({
            "success": True,
            "jobId": job_id,
            "status": "started"
        }), 200
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
        
        # Handle max_listings: if max_pages > 1 and max_listings not provided, use None (scrape all)
        max_listings_param = request.args.get('max_listings')
        if max_listings_param:
            max_listings = int(max_listings_param)
        else:
            # Not provided - check if max_pages > 1
            if max_pages > 1:
                max_listings = None  # Scrape all listings when multiple pages
            else:
                max_listings = 5  # Default for single page
        
        location = request.args.get('location', '')
        location = _normalize_location(location)
        
        save_to_sheets = request.args.get('save_to_sheets', 'true').lower() == 'true'
        
        data = {
            "category_url": category_url,
            "max_pages": max_pages,
            "max_listings": max_listings,
            "location": location,
            "save_to_sheets": save_to_sheets
        }

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


@app.route('/debug/scrape_once', methods=['GET', 'POST'])
def debug_scrape_once():
    """
    Debug endpoint: run a single-page scrape with max_listings<=5 and return results inline.
    Does NOT trigger callback and does NOT save to Google Sheets.
    """
    try:
        if request.method == "POST":
            data = request.get_json() or {}
            params = _parse_scrape_params(data)
        else:
            data = {
                "category_url": request.args.get("category_url"),
                "max_pages": 1,
                "max_listings": request.args.get("max_listings"),
                "location": request.args.get("location", ""),
                "save_to_sheets": False,
            }
            params = _parse_scrape_params(data)

        params["max_pages"] = 1
        # cap to 5 for safety
        if params.get("max_listings") is None:
            params["max_listings"] = 5
        params["max_listings"] = min(int(params["max_listings"]), 5)
        params["save_to_sheets"] = False

        scraper = GumtreeScraper()
        started = time.time()
        print(f"🐞 debug_scrape_once started category={params['category_url']} max_listings={params['max_listings']}")
        sys.stdout.flush()
        try:
            listings = scraper.scrape_category(
                category=params["category_url"],
                location=params["location"],
                max_pages=params["max_pages"],
                max_listings=params["max_listings"],
            )
        finally:
            try:
                scraper.close()
            except Exception:
                pass

        elapsed = time.time() - started
        print(f"🐞 debug_scrape_once finished duration={elapsed:.2f}s listings={len(listings)}")
        sys.stdout.flush()

        return jsonify({"success": True, "listings": listings, "duration_s": elapsed}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500

if __name__ == '__main__':
    # Run the server
    port = int(os.environ.get('PORT', 5001))  # Changed to 5001 to avoid AirPlay conflict
    host = os.environ.get('HOST', '0.0.0.0')
    
    print(f"Starting Gumtree Scraper API server on {host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"Scrape endpoint: http://{host}:{port}/scrape")
    
    app.run(host=host, port=port, debug=False)
