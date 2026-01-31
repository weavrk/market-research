import os
import json
import sys

# Try to import dependencies with better error handling
try:
    import pandas as pd
except ImportError as e:
    print(f"Warning: pandas not available: {e}", file=sys.stderr)
    pd = None

from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename

try:
    import googlemaps
except ImportError as e:
    print(f"Warning: googlemaps not available: {e}", file=sys.stderr)
    googlemaps = None

try:
    from dotenv import load_dotenv
    # Load environment variables (silently fail if .env doesn't exist)
    try:
        load_dotenv()
    except Exception:
        pass  # Continue without .env file
except ImportError:
    load_dotenv = None

try:
    from geopy.distance import geodesic
except ImportError as e:
    print(f"Warning: geopy not available: {e}", file=sys.stderr)
    geodesic = None

import logging
import requests
from datetime import datetime, timedelta
import uuid
import re

try:
    import pgeocode
except ImportError as e:
    print(f"Warning: pgeocode not available: {e}", file=sys.stderr)
    pgeocode = None

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')

# Configure application root for subdirectory deployment
app.config['APPLICATION_ROOT'] = '/hrefs/market-research'

# Disable strict slashes to handle URL variations
app.url_map.strict_slashes = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Google Maps client
api_key = os.getenv('GOOGLE_MAPS_API_KEY')
if api_key and api_key != 'your_google_maps_api_key_here':
    gmaps = googlemaps.Client(key=api_key)
else:
    gmaps = None
    print("Warning: Google Maps API key not configured. Please set GOOGLE_MAPS_API_KEY in your .env file.")

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Simple file-based database for saved retailer results
DATA_DIR = 'data'
DB_FILE = os.path.join(DATA_DIR, 'retailer_database.json')
MARKETS_DB_FILE = os.path.join(DATA_DIR, 'markets_database.json')
os.makedirs(DATA_DIR, exist_ok=True)

def _load_db():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def _save_db(records):
    with open(DB_FILE, 'w') as f:
        json.dump(records, f, indent=2)

def _load_markets_db():
    """Load markets/zip data from file-based database."""
    if not os.path.exists(MARKETS_DB_FILE):
        return []
    try:
        with open(MARKETS_DB_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def _save_markets_db(records):
    """Save markets/zip data to file-based database."""
    with open(MARKETS_DB_FILE, 'w') as f:
        json.dump(records, f, indent=2)

# In-memory cache for large search results (session stores only a token)
LAST_RESULTS_CACHE = {}
LAST_RESULTS_TTL_SECONDS = 60 * 30  # 30 minutes

def _cleanup_cache():
    now = datetime.utcnow().timestamp()
    expired = [k for k, v in LAST_RESULTS_CACHE.items() if now - v.get('ts', now) > LAST_RESULTS_TTL_SECONDS]
    for k in expired:
        LAST_RESULTS_CACHE.pop(k, None)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _parse_address_components(formatted_address):
    """
    Parse formatted address into street, city, state, and zip code components.
    
    Args:
        formatted_address (str): Full formatted address from Google Places API
        Format: "Street, City, State ZIP, Country"
        
    Returns:
        tuple: (street_address, city, state, zip_code)
    """
    if not formatted_address:
        return '', '', '', ''
    
    import re
    
    # Split address by commas
    parts = [part.strip() for part in formatted_address.split(',')]
    
    street_address = ''
    city = ''
    state = ''
    zip_code = ''
    
    if len(parts) >= 3:
        # Format: "Street, City, State ZIP, Country"
        # parts[0] = Street
        # parts[1] = City  
        # parts[2] = State ZIP
        # parts[3] = Country (optional)
        
        street_address = parts[0].strip()
        city = parts[1].strip()
        
        # Parse state and zip from parts[2]
        state_zip_part = parts[2].strip()
        state_zip_match = re.match(r'^([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$', state_zip_part)
        if state_zip_match:
            state = state_zip_match.group(1)
            zip_code = state_zip_match.group(2)
        else:
            # Fallback: try to extract just state
            state_match = re.match(r'^([A-Z]{2})', state_zip_part)
            if state_match:
                state = state_match.group(1)
    
    elif len(parts) == 2:
        # Fallback for simpler format: "Street, City State ZIP"
        street_address = parts[0].strip()
        city_part = parts[1].strip()
        city_state_zip_match = re.match(r'^(.+?)\s+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$', city_part)
        if city_state_zip_match:
            city = city_state_zip_match.group(1).strip()
            state = city_state_zip_match.group(2)
            zip_code = city_state_zip_match.group(3)
    
    return street_address, city, state, zip_code

def is_official_brand_store(place_name: str, retailer_name: str) -> bool:
    """Return True if the place name looks like an official brand store, not a reseller.

    Heuristics:
    - Name must contain the brand (case-insensitive), allowing common variants like "Polo <Brand>" or "<Brand> Outlet".
    - Exclude known department/reseller chains by name.
    - More lenient matching for partial brand names.
    """
    if not place_name:
        return False

    name_l = place_name.lower()
    brand_l = retailer_name.lower().strip()

    # Known reseller/department chains to exclude (extendable)
    excluded_names = [
        'macy', 'nordstrom', 'dillard', 'bloomingdale', 'saks', 'neiman marcus',
        'kohls', 'jcpenney', 'tj maxx', 'marshalls', 'ross dress', 'burlington',
        'target', 'walmart', 'costco', 'sam\'s club', 'amazon hub', 'belk'
    ]
    if any(x in name_l for x in excluded_names):
        return False

    # Accept if exact brand mention in name
    if brand_l in name_l:
        return True

    # More lenient matching: accept if any significant word from brand appears
    brand_tokens = [t for t in brand_l.split() if len(t) > 2]  # Only words longer than 2 chars
    if brand_tokens:
        # Accept if any significant brand word appears in the store name
        if any(token in name_l for token in brand_tokens):
            return True

    # Accept common variants (e.g., "Polo Ralph Lauren", "Lauren Ralph Lauren")
    tokens = [t for t in brand_l.split() if t]
    if len(tokens) >= 2:
        # Any ordering of tokens appears in the name
        if all(t in name_l for t in tokens):
            return True

    # Accept prefix variants like "Polo <Brand>", "Factory <Brand>", "Outlet <Brand>"
    variant_prefixes = ['polo', 'factory', 'outlet', 'ralph', 'lauren']
    for vp in variant_prefixes:
        if f"{vp} {brand_l}" in name_l:
            return True
        # Also check if the variant + any brand word appears
        for token in brand_tokens:
            if f"{vp} {token}" in name_l:
                return True

    return False

def get_google_cloud_billing_data():
    """
    Return near real-time billing from BigQuery export if configured.
    Requires these env vars and a configured detailed usage cost export:
      - BILLING_EXPORT_PROJECT
      - BILLING_EXPORT_DATASET
      - BILLING_EXPORT_TABLE (e.g., gcp_billing_export_v1_XXXX)
      - GOOGLE_APPLICATION_CREDENTIALS (service account with BigQuery read)
    """
    try:
        export_project = os.getenv('BILLING_EXPORT_PROJECT')
        export_dataset = os.getenv('BILLING_EXPORT_DATASET')
        export_table = os.getenv('BILLING_EXPORT_TABLE')

        if not (export_project and export_dataset and export_table):
            # Not configured; return placeholders so UI still renders
            return {
                'current_month': datetime.now().strftime('%Y-%m'),
                'current_date': datetime.now().strftime('%Y-%m-%d'),
                'monthly_total': 0.0,
                'daily_total': 0.0,
                'api_breakdown': {
                    'places_api': 0.0,
                    'geocoding_api': 0.0,
                    'maps_javascript_api': 0.0
                },
                'quota_usage': {
                    'places_api_requests': 0,
                    'geocoding_requests': 0,
                    'maps_loads': 0
                },
                'billing_status': 'not_configured',
                'free_tier_remaining': 200.0,
                'last_updated': datetime.now().isoformat()
            }

        # Lazy import to avoid hard dependency if not used
        from google.cloud import bigquery

        client = bigquery.Client(project=export_project)
        table_fqn = f"`{export_project}.{export_dataset}.{export_table}`"

        # Aggregate month-to-date and today totals (net of credits)
        sql_totals = f'''
        WITH base AS (
          SELECT
            DATE(usage_start_time) AS usage_date,
            service.description AS service_desc,
            cost,
            (SELECT SUM(c.amount) FROM UNNEST(credits) c) AS credits_sum
          FROM {table_fqn}
          WHERE invoice.month = FORMAT_DATE('%Y%m', CURRENT_DATE())
        )
        SELECT
          (SELECT COALESCE(SUM(cost + COALESCE(credits_sum, 0)), 0) FROM base) AS mtd_total,
          (SELECT COALESCE(SUM(cost + COALESCE(credits_sum, 0)), 0) FROM base WHERE usage_date = CURRENT_DATE()) AS today_total;
        '''

        totals = list(client.query(sql_totals).result())[0]
        monthly_total = float(totals[0] or 0.0)
        daily_total = float(totals[1] or 0.0)

        # Per-service breakdown for key Maps APIs (month-to-date)
        sql_breakdown = f'''
        WITH base AS (
          SELECT
            service.description AS service_desc,
            cost,
            (SELECT SUM(c.amount) FROM UNNEST(credits) c) AS credits_sum
          FROM {table_fqn}
          WHERE invoice.month = FORMAT_DATE('%Y%m', CURRENT_DATE())
        )
        SELECT
          LOWER(service_desc) AS svc,
          SUM(cost + COALESCE(credits_sum, 0)) AS net_cost
        FROM base
        GROUP BY svc;
        '''

        breakdown_rows = list(client.query(sql_breakdown).result())
        svc_to_cost = {row[0]: float(row[1] or 0.0) for row in breakdown_rows}

        def pick(keys):
            for k in keys:
                if k in svc_to_cost:
                    return svc_to_cost[k]
            return 0.0

        api_breakdown = {
            'places_api': pick(['places api', 'places']),
            'geocoding_api': pick(['geocoding api', 'geocoding']),
            'maps_javascript_api': pick(['maps javascript api', 'maps javascript'])
        }

        # Quota-like usage approximation (counts of export rows per service today)
        sql_usage = f'''
        SELECT LOWER(service.description) AS svc, COUNT(1) AS cnt
        FROM {table_fqn}
        WHERE DATE(usage_start_time) = CURRENT_DATE()
        GROUP BY svc;
        '''
        usage_rows = list(client.query(sql_usage).result())
        svc_to_cnt = {row[0]: int(row[1] or 0) for row in usage_rows}

        def pick_cnt(keys):
            for k in keys:
                if k in svc_to_cnt:
                    return svc_to_cnt[k]
            return 0

        quota_usage = {
            'places_api_requests': pick_cnt(['places api', 'places']),
            'geocoding_requests': pick_cnt(['geocoding api', 'geocoding']),
            'maps_loads': pick_cnt(['maps javascript api', 'maps javascript'])
        }

        return {
            'current_month': datetime.now().strftime('%Y-%m'),
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'monthly_total': round(monthly_total, 4),
            'daily_total': round(daily_total, 4),
            'api_breakdown': api_breakdown,
            'quota_usage': quota_usage,
            'billing_status': 'active',
            'free_tier_remaining': max(0.0, 200.0 - monthly_total),
            'last_updated': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting billing data: {e}")
        return {
            'current_month': datetime.now().strftime('%Y-%m'),
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'monthly_total': 0.0,
            'daily_total': 0.0,
            'api_breakdown': {
                'places_api': 0.0,
                'geocoding_api': 0.0,
                'maps_javascript_api': 0.0
            },
            'quota_usage': {
                'places_api_requests': 0,
                'geocoding_requests': 0,
                'maps_loads': 0
            },
            'billing_status': 'error',
            'free_tier_remaining': 200.0,
            'last_updated': datetime.now().isoformat()
        }

def search_retailer_stores(retailer_name, location="United States", radius=50000):
    """
    Search for retailer stores using Google Places API.
    
    Args:
        retailer_name (str): Name of the retailer to search for
        location (str): Location to search around (default: "United States")
        radius (int): Search radius in meters (default: 50km)
    
    Returns:
        list: List of store information dictionaries
    """
    if not gmaps:
        logger.error("Google Maps API client not initialized. Please configure your API key.")
        return []
    
    try:
        # Geocode the location to get coordinates
        geocode_result = gmaps.geocode(location)
        if not geocode_result:
            logger.error(f"Could not geocode location: {location}")
            return []
        
        location_coords = geocode_result[0]['geometry']['location']
        
        # Search for places (bias results by name)
        places_result = gmaps.places_nearby(
            location=location_coords,
            radius=radius,
            name=retailer_name,
            type='store'
        )
        
        stores = []
        for place in places_result.get('results', []):
            place_name = place.get('name', '')
            if not is_official_brand_store(place_name, retailer_name):
                continue

            store_info = {
                'name': place_name,
                'address': place.get('vicinity', ''),
                'rating': place.get('rating', 0),
                'user_ratings_total': place.get('user_ratings_total', 0),
                'place_id': place.get('place_id', ''),
                'latitude': place['geometry']['location']['lat'],
                'longitude': place['geometry']['location']['lng'],
                'types': place.get('types', []),
                'business_status': place.get('business_status', ''),
                'price_level': place.get('price_level', None)
            }
            stores.append(store_info)
        
        # Get detailed information for each place
        for store in stores:
            if store['place_id']:
                try:
                    place_details = gmaps.place(
                        place_id=store['place_id'],
                        fields=['formatted_address', 'formatted_phone_number', 'opening_hours', 'website']
                    )
                    
                    details = place_details.get('result', {})
                    store['formatted_address'] = details.get('formatted_address', store['address'])
                    store['phone_number'] = details.get('formatted_phone_number', '')
                    store['opening_hours'] = details.get('opening_hours', {})
                    store['website'] = details.get('website', '')
                    
                except Exception as e:
                    logger.warning(f"Could not get details for place {store['place_id']}: {e}")
        
        return stores
        
    except Exception as e:
        logger.error(f"Error searching for stores: {e}")
        return []

def cross_reference_stores(google_stores, csv_data, distance_threshold=1.0):
    """
    Cross-reference Google Places results with CSV data.
    
    Args:
        google_stores (list): List of stores from Google Places API
        csv_data (DataFrame): CSV data with store information
        distance_threshold (float): Maximum distance in miles for matching
    
    Returns:
        dict: Cross-referenced results
    """
    matches = []
    unmatched_google = []
    unmatched_csv = []
    
    # Create a copy of CSV data for tracking unmatched entries
    csv_remaining = csv_data.copy()
    
    for google_store in google_stores:
        google_coords = (google_store['latitude'], google_store['longitude'])
        best_match = None
        best_distance = float('inf')
        best_csv_index = None
        
        for idx, csv_row in csv_remaining.iterrows():
            # Check if CSV has latitude/longitude columns
            if 'latitude' in csv_row and 'longitude' in csv_row:
                csv_coords = (csv_row['latitude'], csv_row['longitude'])
                distance = geodesic(google_coords, csv_coords).miles
                
                if distance <= distance_threshold and distance < best_distance:
                    best_match = csv_row
                    best_distance = distance
                    best_csv_index = idx
            
            # Also try matching by name similarity
            elif 'name' in csv_row or 'store_name' in csv_row:
                csv_name = csv_row.get('name', csv_row.get('store_name', '')).lower()
                google_name = google_store['name'].lower()
                
                # Simple name matching (can be improved with fuzzy matching)
                if csv_name in google_name or google_name in csv_name:
                    if best_match is None:  # Only use name matching if no location match
                        best_match = csv_row
                        best_distance = 0  # Name match
                        best_csv_index = idx
        
        if best_match is not None and best_distance <= distance_threshold:
            matches.append({
                'google_store': google_store,
                'csv_data': best_match.to_dict(),
                'distance': best_distance,
                'match_type': 'location' if best_distance > 0 else 'name'
            })
            csv_remaining = csv_remaining.drop(best_csv_index)
        else:
            unmatched_google.append(google_store)
    
    # Remaining CSV entries are unmatched
    unmatched_csv = csv_remaining.to_dict('records')
    
    return {
        'matches': matches,
        'unmatched_google': unmatched_google,
        'unmatched_csv': unmatched_csv,
        'summary': {
            'total_google_stores': len(google_stores),
            'total_csv_stores': len(csv_data),
            'matches_found': len(matches),
            'unmatched_google': len(unmatched_google),
            'unmatched_csv': len(unmatched_csv)
        }
    }

@app.route('/favicon.ico')
def favicon():
    """Serve favicon.ico to prevent 404 errors."""
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    """Main page with search form and file upload."""
    return render_template('index.html')

def _migrate_retailer_data():
    """Migrate existing retailer data to include total_cities and filter closed stores."""
    retailer_data = _load_db()
    updated = False
    
    for retailer in retailer_data:
        # Skip if already migrated
        if 'total_cities' in retailer:
            continue
            
        # Filter out permanently closed stores
        active_stores = []
        for store in retailer.get('stores', []):
            business_status = store.get('business_status', '').lower()
            if business_status not in ['permanently_closed', 'closed_permanently']:
                active_stores.append(store)
        
        # Count unique cities from active stores
        unique_cities = set()
        for store in active_stores:
            city = store.get('city', '').strip()
            if city:
                unique_cities.add(city)
        
        # Update retailer data
        retailer['stores'] = active_stores
        retailer['total_stores'] = len(active_stores)
        retailer['total_cities'] = len(unique_cities)
        updated = True
        
        logger.info(f"Migrated retailer '{retailer.get('retailer_name', 'Unknown')}': {len(active_stores)} active stores across {len(unique_cities)} cities")
    
    if updated:
        _save_db(retailer_data)
        logger.info("Retailer database migration completed")
    
    return retailer_data

@app.route('/retailer-database')
def retailer_database():
    """Retailer Database page showing saved retailer data."""
    # Migrate existing data if needed
    all_retailer_data = _migrate_retailer_data()
    # Filter out removed retailers for display, but keep them in the data for restore functionality
    active_retailers = [r for r in all_retailer_data if not r.get('removed', False)]
    logger.info(f"Retailer database page loaded with {len(active_retailers)} active retailers out of {len(all_retailer_data)} total")
    return render_template('retailer_database.html', retailer_data=all_retailer_data, api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '')

@app.route('/usage')
def usage():
    """Embed the Google Cloud Billing page; shows fallback link if blocked by browser."""
    billing_url = "https://console.cloud.google.com/billing/017DF5-773A3D-847C0E?organizationId=61770565445"
    return render_template('usage.html', billing_url=billing_url)

@app.route('/markets', methods=['GET', 'POST'])
def markets():
    """Live Markets page with CSV upload and simple visualization of first two columns.
    Column 1 assumed to be ZIP, column 2 City; extra columns are ignored.
    """
    table_rows = []
    headers = ['Zip Code', 'City']

    # On GET requests, try to load data from session first, then from persistent database
    if request.method == 'GET':
        # Try session first
        table_rows = session.get('markets_rows', [])
        
        # If no session data, load from persistent database (most recent upload)
        if not table_rows:
            markets_db = _load_markets_db()
            if markets_db:
                table_rows = markets_db[-1]['data']  # Get most recent upload
                # Also restore to session for immediate use
                session['markets_rows'] = table_rows
                session.modified = True
                logger.info(f"Loaded {len(table_rows)} Live Markets entries from persistent database to session")

    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename:
            flash('Please choose a CSV file to upload.', 'warning')
            return render_template('markets.html', headers=headers, rows=table_rows, api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '')

        if not allowed_file(file.filename):
            flash('Only .csv files are allowed.', 'error')
            return render_template('markets.html', headers=headers, rows=table_rows, api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '')

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        try:
            df = pd.read_csv(filepath)
            nomi = pgeocode.Nominatim('us')
            city_state_entries = df.iloc[:, 0].dropna().astype(str).str.strip()
            zip_city_rows = []

            # Helper: pull zips from Zippopotam (requires state), fallback to pgeocode
            def zips_from_zippopotam(state_abbr: str, city_name: str):
                try:
                    from urllib.parse import quote
                    url = f"https://api.zippopotam.us/us/{state_abbr.lower()}/{quote(city_name)}"
                    resp = requests.get(url, timeout=10)
                    if resp.status_code != 200:
                        return []
                    data = resp.json()
                    out = []
                    for p in data.get('places', []) or []:
                        z = p.get('post code') or p.get('postcode') or p.get('post_code') or p.get('postal_code')
                        pn = p.get('place name') or p.get('place_name') or city_name
                        if z:
                            out.append({'Zip Code': str(z), 'City': str(pn)})
                    return out
                except Exception:
                    return []

            geo_df = nomi._data
            for entry in city_state_entries.unique():
                if not entry:
                    continue
                
                # Parse "City, State" format
                if ',' in entry:
                    parts = entry.split(',')
                    city = parts[0].strip()
                    state = parts[1].strip().upper()
                else:
                    # Fallback: treat as city only and find states from pgeocode
                    city = entry
                    
                    # First, try well-known major city mappings
                    major_cities = {
                        'houston': 'TX', 'dallas': 'TX', 'san antonio': 'TX', 'austin': 'TX', 'fort worth': 'TX',
                        'phoenix': 'AZ', 'tucson': 'AZ', 'mesa': 'AZ', 'chandler': 'AZ',
                        'los angeles': 'CA', 'san diego': 'CA', 'san jose': 'CA', 'san francisco': 'CA',
                        'fresno': 'CA', 'sacramento': 'CA', 'long beach': 'CA', 'oakland': 'CA',
                        'chicago': 'IL', 'aurora': 'IL', 'rockford': 'IL', 'joliet': 'IL',
                        'philadelphia': 'PA', 'pittsburgh': 'PA', 'allentown': 'PA', 'erie': 'PA',
                        'new york': 'NY', 'buffalo': 'NY', 'rochester': 'NY', 'yonkers': 'NY',
                        'miami': 'FL', 'tampa': 'FL', 'orlando': 'FL', 'st. petersburg': 'FL',
                        'atlanta': 'GA', 'augusta': 'GA', 'columbus': 'GA', 'savannah': 'GA',
                        'nashville': 'TN', 'memphis': 'TN', 'knoxville': 'TN', 'chattanooga': 'TN',
                        'denver': 'CO', 'colorado springs': 'CO', 'aurora': 'CO', 'fort collins': 'CO',
                        'seattle': 'WA', 'spokane': 'WA', 'tacoma': 'WA', 'vancouver': 'WA',
                        'portland': 'OR', 'salem': 'OR', 'eugene': 'OR', 'gresham': 'OR',
                        'las vegas': 'NV', 'henderson': 'NV', 'reno': 'NV', 'north las vegas': 'NV',
                        'boston': 'MA', 'worcester': 'MA', 'springfield': 'MA', 'cambridge': 'MA',
                        'detroit': 'MI', 'grand rapids': 'MI', 'warren': 'MI', 'sterling heights': 'MI',
                        'minneapolis': 'MN', 'saint paul': 'MN', 'rochester': 'MN', 'duluth': 'MN',
                        'kansas city': 'MO', 'saint louis': 'MO', 'springfield': 'MO', 'independence': 'MO',
                        'cleveland': 'OH', 'cincinnati': 'OH', 'toledo': 'OH', 'akron': 'OH',
                        'columbus': 'OH', 'dayton': 'OH', 'parma': 'OH', 'canton': 'OH',
                        'indianapolis': 'IN', 'fort wayne': 'IN', 'evansville': 'IN', 'south bend': 'IN',
                        'milwaukee': 'WI', 'madison': 'WI', 'green bay': 'WI', 'kenosha': 'WI',
                        'baltimore': 'MD', 'frederick': 'MD', 'rockville': 'MD', 'gaithersburg': 'MD',
                        'charlotte': 'NC', 'raleigh': 'NC', 'greensboro': 'NC', 'durham': 'NC',
                        'virginia beach': 'VA', 'norfolk': 'VA', 'chesapeake': 'VA', 'richmond': 'VA',
                        'salt lake city': 'UT', 'west valley city': 'UT', 'provo': 'UT', 'west jordan': 'UT',
                        'oklahoma city': 'OK', 'tulsa': 'OK', 'norman': 'OK', 'broken arrow': 'OK',
                        'louisville': 'KY', 'lexington': 'KY', 'bowling green': 'KY', 'owensboro': 'KY',
                        'new orleans': 'LA', 'baton rouge': 'LA', 'shreveport': 'LA', 'lafayette': 'LA',
                        'albuquerque': 'NM', 'las cruces': 'NM', 'rio rancho': 'NM', 'santa fe': 'NM',
                        'omaha': 'NE', 'lincoln': 'NE', 'bellevue': 'NE', 'grand island': 'NE',
                        'wichita': 'KS', 'overland park': 'KS', 'kansas city': 'KS', 'topeka': 'KS',
                        'des moines': 'IA', 'cedar rapids': 'IA', 'davenport': 'IA', 'sioux city': 'IA',
                        'little rock': 'AR', 'fort smith': 'AR', 'fayetteville': 'AR',
                        'jackson': 'MS', 'gulfport': 'MS', 'southaven': 'MS', 'hattiesburg': 'MS',
                        'birmingham': 'AL', 'montgomery': 'AL', 'mobile': 'AL', 'huntsville': 'AL',
                        'anchorage': 'AK', 'fairbanks': 'AK', 'juneau': 'AK',
                        'honolulu': 'HI', 'pearl city': 'HI', 'hilo': 'HI',
                        'boise': 'ID', 'nampa': 'ID', 'meridian': 'ID', 'idaho falls': 'ID',
                        'billings': 'MT', 'missoula': 'MT', 'great falls': 'MT', 'bozeman': 'MT',
                        'fargo': 'ND', 'bismarck': 'ND', 'grand forks': 'ND', 'minot': 'ND',
                        'sioux falls': 'SD', 'rapid city': 'SD', 'aberdeen': 'SD', 'brookings': 'SD',
                        'cheyenne': 'WY', 'casper': 'WY', 'laramie': 'WY', 'gillette': 'WY',
                        'burlington': 'VT', 'essex': 'VT', 'south burlington': 'VT', 'colchester': 'VT',
                        'concord': 'NH', 'manchester': 'NH', 'nashua': 'NH', 'derry': 'NH',
                        'providence': 'RI', 'warwick': 'RI', 'cranston': 'RI', 'pawtucket': 'RI',
                        'hartford': 'CT', 'bridgeport': 'CT', 'new haven': 'CT', 'stamford': 'CT',
                        'dover': 'DE', 'wilmington': 'DE',
                        'annapolis': 'MD', 'bowie': 'MD', 'hagerstown': 'MD',
                        'charleston': 'WV', 'huntington': 'WV', 'parkersburg': 'WV', 'morgantown': 'WV',
                        'columbia': 'SC', 'charleston': 'SC', 'north charleston': 'SC', 'mount pleasant': 'SC',
                        'tallahassee': 'FL', 'fort lauderdale': 'FL', 'port st. lucie': 'FL', 'cape coral': 'FL',
                        'washington': 'DC'
                    }
                    
                    city_lower = city.lower().strip()
                    if city_lower in major_cities:
                        state = major_cities[city_lower]
                        logger.info(f"Using known mapping: {city} -> {state}")
                    else:
                        # Fall back to pgeocode lookup
                        mask_city = geo_df['place_name'].str.casefold() == city.casefold()
                        cand_states = (
                            geo_df.loc[mask_city, 'state_code']
                            .dropna()
                            .astype(str)
                            .str.upper()
                            .unique()
                            .tolist()
                        )
                        if not cand_states:
                            continue
                            
                        # Use the most common state for this city (by count of zip codes)
                        state_counts = geo_df.loc[mask_city, 'state_code'].value_counts()
                        if len(state_counts) > 0:
                            state = state_counts.index[0].upper()  # Most common state
                            logger.info(f"Using most common state from pgeocode: {city} -> {state}")
                        else:
                            state = cand_states[0]  # Fallback to first found
                            logger.info(f"Using first found state from pgeocode: {city} -> {state}")
                
                # Collect all ZIP codes for this city
                zip_codes = set()
                
                # Try Zippopotam first with the parsed state
                rows = zips_from_zippopotam(state, city)
                if rows:
                    for row in rows:
                        zip_codes.add(row['Zip Code'])
                else:
                    # Fallback: pgeocode only
                    mask_city = geo_df['place_name'].str.casefold() == city.casefold()
                    mask_state = geo_df['state_code'].str.upper() == state
                    combined_mask = mask_city & mask_state
                    res = geo_df.loc[combined_mask, ['postal_code']].dropna().drop_duplicates()
                    for _, r in res.iterrows():
                        zip_codes.add(str(r['postal_code']))
                
                # Create single row with comma-separated ZIP codes
                if zip_codes:
                    zip_city_rows.append({
                        'City': city,
                        'State': state,
                        'Zip Codes': ', '.join(sorted(zip_codes))
                    })

            table_rows = zip_city_rows
            flash(f'Found {len(table_rows)} ZIP entries from {len(city_state_entries.unique())} cities.', 'success')
            
            # Save to both session (for immediate use) and file-based database (for persistence)
            session['markets_rows'] = table_rows
            session.modified = True
            
            # Save to persistent file-based database
            markets_entry = {
                'filename': filename,
                'data': table_rows,
                'total_entries': len(table_rows),
                'total_cities': len(city_state_entries.unique()),
                'date_uploaded': datetime.now().isoformat()
            }
            
            # Load existing markets data and add new entry
            existing_markets = _load_markets_db()
            existing_markets.append(markets_entry)
            _save_markets_db(existing_markets)
            
            logger.info(f"Cached {len(table_rows)} Live Markets entries in session and saved to persistent database")
        except Exception as e:
            flash(f'Error reading CSV: {e}', 'error')
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    return render_template('markets.html', headers=headers, rows=table_rows, api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '')

@app.route('/clear-markets', methods=['POST'])
def clear_markets():
    """Clear all markets data from session and persistent storage."""
    try:
        # Clear from session
        session.pop('markets_rows', None)
        
        # Clear from persistent storage
        persistent_file = 'data/markets_database.json'
        if os.path.exists(persistent_file):
            with open(persistent_file, 'w') as f:
                json.dump([], f)
        
        logger.info("Cleared all markets data from session and persistent storage")
        return jsonify({'success': True, 'message': 'All markets data cleared successfully'})
    
    except Exception as e:
        logger.error(f"Error clearing markets data: {e}")
        return jsonify({'success': False, 'error': str(e)})

def _extract_zip_from_address(address: str) -> str:
    if not address:
        return ''
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b", address)
    return m.group(1) if m else ''

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    results = []
    if request.method == 'POST':
        logger.info("Analyze: POST request received")
        # Try to get markets data from session first, then fall back to file-based storage
        markets_rows = session.get('markets_rows', [])
        if not markets_rows:
            # Load from persistent file-based database (get most recent entry)
            markets_db = _load_markets_db()
            if markets_db:
                markets_rows = markets_db[-1]['data']  # Get most recent upload
                logger.info(f"Analyze: Loaded {len(markets_rows)} ZIP entries from persistent database")
            else:
                logger.info("Analyze: No Live Markets data found in session or persistent database")
        
        retailer_records = _load_db()
        logger.info(f"Analyze: Using {len(markets_rows)} List Market Zip Codes entries and {len(retailer_records)} retailer records")
        
        if not markets_rows:
            flash('No Live Markets data found. Please upload a CSV file in the Live Markets section first.', 'warning')
            return render_template('analyze.html', results=results, api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '')
        
        if not retailer_records:
            flash('No retailer data found. Please add retailers to the database first.', 'warning')
            return render_template('analyze.html', results=results, api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '')

        # Map retailer locations by ZIP -> dict of retailer names and their counts
        retailer_by_zip = {}
        processed_retailers = 0
        skipped_retailers = 0
        
        for retailer_entry in retailer_records:
            # Handle new structure: retailer_entry has 'stores' array
            if 'stores' in retailer_entry:
                stores = retailer_entry.get('stores', [])
                for store in stores:
                    name = store.get('name', '')
                    address = store.get('formatted_address') or store.get('address', '')
                    z = _extract_zip_from_address(address)
                    
                    if not z or not name:
                        skipped_retailers += 1
                        logger.debug(f"Skipped store: name='{name}', address='{address}', zip='{z}'")
                        continue
                    
                    if z not in retailer_by_zip:
                        retailer_by_zip[z] = {}
                    retailer_by_zip[z][name] = retailer_by_zip[z].get(name, 0) + 1
                    processed_retailers += 1
            else:
                # Handle old structure: individual store records
                name = retailer_entry.get('name') or retailer_entry.get('google_store', {}).get('name', '')
                address = retailer_entry.get('formatted_address') or retailer_entry.get('address') or retailer_entry.get('google_store', {}).get('formatted_address', '')
                z = _extract_zip_from_address(address)
                
                if not z or not name:
                    skipped_retailers += 1
                    logger.debug(f"Skipped retailer: name='{name}', address='{address}', zip='{z}'")
                    continue
                
                if z not in retailer_by_zip:
                    retailer_by_zip[z] = {}
                retailer_by_zip[z][name] = retailer_by_zip[z].get(name, 0) + 1
                processed_retailers += 1
        
        logger.info(f"Retailer processing: {processed_retailers} processed, {skipped_retailers} skipped, {len(retailer_by_zip)} unique zip codes")

        # Create a set of all market zip codes for reflex market checking
        all_market_zips = set()
        for row in markets_rows:
            zip_codes_str = (row.get('Zip Codes') or row.get('Zip Code') or '').strip()
            if zip_codes_str:
                zip_codes = [z.strip() for z in zip_codes_str.split(',') if z.strip()]
                all_market_zips.update(zip_codes)
        
        # Group retailer locations by city -> aggregate all retailers and stores per city
        city_aggregated_data = {}
        matched_zips = 0
        unmatched_zips = 0
        
        for zip_code, retailers in retailer_by_zip.items():
            # Get city name for this zip code from markets data or use zip code as fallback
            city_name = None
            for row in markets_rows:
                zip_codes_str = (row.get('Zip Codes') or row.get('Zip Code') or '').strip()
                if zip_codes_str:
                    zip_codes = [z.strip() for z in zip_codes_str.split(',') if z.strip()]
                    if zip_code in zip_codes:
                        city_name = (row.get('City') or '').strip()
                        break
            
            # If no city found in markets data, try to get city name from retailer data
            if not city_name:
                # Look through retailer data to find a city name for this zip code
                for retailer_entry in retailer_records:
                    if 'stores' in retailer_entry:
                        stores = retailer_entry.get('stores', [])
                        for store in stores:
                            store_zip = _extract_zip_from_address(store.get('formatted_address') or store.get('address', ''))
                            if store_zip == zip_code and store.get('city'):
                                city_name = store.get('city', '').strip()
                                break
                        if city_name:
                            break
                    else:
                        # Handle old structure
                        store_zip = _extract_zip_from_address(retailer_entry.get('formatted_address') or retailer_entry.get('address', ''))
                        if store_zip == zip_code and retailer_entry.get('city'):
                            city_name = retailer_entry.get('city', '').strip()
                            break
            
            # If still no city found, use zip code as city identifier
            if not city_name:
                city_name = f"ZIP {zip_code}"
                unmatched_zips += 1
            else:
                matched_zips += 1
            
            # Get state information for this zip code
            state_name = None
            for row in markets_rows:
                zip_codes_str = (row.get('Zip Codes') or row.get('Zip Code') or '').strip()
                if zip_codes_str:
                    zip_codes = [z.strip() for z in zip_codes_str.split(',') if z.strip()]
                    if zip_code in zip_codes:
                        state_name = (row.get('State') or '').strip()
                        break
            
            # If no state found in markets data, try to get from retailer data
            if not state_name:
                for retailer_entry in retailer_records:
                    if 'stores' in retailer_entry:
                        stores = retailer_entry.get('stores', [])
                        for store in stores:
                            store_zip = _extract_zip_from_address(store.get('formatted_address') or store.get('address', ''))
                            if store_zip == zip_code and store.get('state'):
                                state_name = store.get('state', '').strip()
                                break
                        if state_name:
                            break
                    else:
                        # Handle old structure
                        store_zip = _extract_zip_from_address(retailer_entry.get('formatted_address') or retailer_entry.get('address', ''))
                        if store_zip == zip_code and retailer_entry.get('state'):
                            state_name = retailer_entry.get('state', '').strip()
                            break
            
            # If still no state found, use empty string
            if not state_name:
                state_name = ''
            
            # Initialize city data if not exists
            if city_name not in city_aggregated_data:
                city_aggregated_data[city_name] = {
                    'retailers': {},
                    'zip_codes': set(),
                    'is_reflex_market': False,
                    'state': state_name
                }
            
            # Aggregate retailers and stores for this city
            for retailer, count in retailers.items():
                city_aggregated_data[city_name]['retailers'][retailer] = city_aggregated_data[city_name]['retailers'].get(retailer, 0) + count
            
            # Add zip code to city
            city_aggregated_data[city_name]['zip_codes'].add(zip_code)
            
            # Check if this zip code is in market data (reflex market)
            if zip_code in all_market_zips:
                city_aggregated_data[city_name]['is_reflex_market'] = True
        
        logger.info(f"City aggregation: {matched_zips} zip codes matched to cities, {unmatched_zips} unmatched, {len(city_aggregated_data)} total cities")
        
        # Build results per city - showing top cities with most stores
        for city, data in city_aggregated_data.items():
            # Format retailer list with counts
            retailer_list = []
            for retailer, count in sorted(data['retailers'].items()):
                if count > 1:
                    retailer_list.append(f"{retailer} ({count})")
                else:
                    retailer_list.append(retailer)
            
            # Get top 5 zip codes for this city (for reference)
            zip_codes_list = sorted(list(data['zip_codes']))[:5]
            
            results.append({
                'City': city,
                'State': data.get('state', ''),
                'Prioritized Zip Codes': ', '.join(zip_codes_list),
                'Retailers': ', '.join(retailer_list),
                'Total Stores': sum(data['retailers'].values()),
                'Is Reflex Market': data['is_reflex_market']
            })
        
        # Sort results by total stores (descending) to show top cities with most stores first
        results.sort(key=lambda x: x['Total Stores'], reverse=True)
        
        flash(f'Analysis completed! Found {len(results)} cities with retailer data.', 'success')
        logger.info(f"Analyze: Completed analysis with {len(results)} results")

    return render_template('analyze.html', results=results, api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '')

@app.route('/api/zip-cache', methods=['GET'])
def get_zip_cache():
    """API endpoint to check current List Market Zip Codes cache status."""
    # Try to get markets data from session first, then fall back to file-based storage
    markets_rows = session.get('markets_rows', [])
    if not markets_rows:
        # Load from persistent file-based database (get most recent entry)
        markets_db = _load_markets_db()
        if markets_db:
            markets_rows = markets_db[-1]['data']  # Get most recent upload
            logger.info(f"API: Loaded {len(markets_rows)} ZIP entries from persistent database")
    
    return jsonify({
        'cached_entries': len(markets_rows),
        'data': markets_rows,
        'has_data': len(markets_rows) > 0
    })

@app.route('/api/store-details', methods=['POST'])
def get_store_details():
    """API endpoint to get detailed store information for a specific city/state."""
    try:
        data = request.get_json()
        city = data.get('city', '')
        state = data.get('state', '')
        zip_codes = data.get('zip_codes', '')
        retailers = data.get('retailers', '')
        
        logger.info(f"Store details request for: {city}, {state}")
        
        # Load retailer data
        retailer_records = _load_db()
        matching_stores = []
        
        # Parse zip codes
        zip_list = [z.strip() for z in zip_codes.split(',') if z.strip()]
        
        # Find stores matching the criteria
        for retailer_entry in retailer_records:
            if 'stores' in retailer_entry:
                stores = retailer_entry.get('stores', [])
                for store in stores:
                    store_zip = _extract_zip_from_address(store.get('formatted_address') or store.get('address', ''))
                    store_city = store.get('city', '').strip()
                    store_state = store.get('state', '').strip()
                    
                    # Check if store matches the criteria
                    if (store_zip in zip_list or 
                        (store_city.lower() == city.lower() and store_state.lower() == state.lower())):
                        matching_stores.append(store)
            else:
                # Handle old structure
                store_zip = _extract_zip_from_address(retailer_entry.get('formatted_address') or retailer_entry.get('address', ''))
                store_city = retailer_entry.get('city', '').strip()
                store_state = retailer_entry.get('state', '').strip()
                
                if (store_zip in zip_list or 
                    (store_city.lower() == city.lower() and store_state.lower() == state.lower())):
                    matching_stores.append(retailer_entry)
        
        logger.info(f"Found {len(matching_stores)} matching stores")
        
        return jsonify({
            'success': True,
            'stores': matching_stores,
            'count': len(matching_stores)
        })
        
    except Exception as e:
        logger.error(f"Error getting store details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/markets-database', methods=['GET'])
def get_markets_database():
    """API endpoint to get all persistent markets/zip data."""
    try:
        markets_db = _load_markets_db()
        return jsonify({
            'success': True,
            'total_uploads': len(markets_db),
            'uploads': markets_db
        })
    except Exception as e:
        logger.error(f"Error getting markets database: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/markets-database/<int:upload_index>', methods=['DELETE'])
def delete_markets_upload(upload_index):
    """API endpoint to delete a specific markets upload."""
    try:
        markets_db = _load_markets_db()
        
        if upload_index < 0 or upload_index >= len(markets_db):
            return jsonify({'success': False, 'error': 'Invalid upload index'})
        
        deleted_upload = markets_db.pop(upload_index)
        _save_markets_db(markets_db)
        
        logger.info(f"Deleted markets upload: {deleted_upload.get('filename', 'Unknown')}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted upload: {deleted_upload.get("filename", "Unknown")}',
            'remaining_uploads': len(markets_db)
        })
        
    except Exception as e:
        logger.error(f"Error deleting markets upload: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/markets-database/clear', methods=['POST'])
def clear_markets_database():
    """API endpoint to clear all markets/zip data."""
    try:
        _save_markets_db([])
        logger.info("Markets database cleared")
        return jsonify({'success': True, 'message': 'Markets database cleared successfully'})
    except Exception as e:
        logger.error(f"Error clearing markets database: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/search', methods=['POST'])
def search_stores():
    """Search for retailer stores across the US."""
    try:
        retailer_input = request.form.get('retailer_name', '').strip()
        selected_cities_json = request.form.get('selected_cities', '')
        
        if not retailer_input:
            flash('Please enter a retailer name.', 'error')
            return redirect(url_for('index'))
        
        # Parse comma-separated retailer names
        retailer_names = [name.strip() for name in retailer_input.split(',') if name.strip()]
        
        if not retailer_names:
            flash('Please enter at least one retailer name.', 'error')
            return redirect(url_for('index'))
        
        # Parse selected cities from frontend
        selected_cities = []
        if selected_cities_json:
            try:
                selected_cities = json.loads(selected_cities_json)
                logger.info(f"Using {len(selected_cities)} selected cities for search")
            except json.JSONDecodeError:
                logger.warning("Failed to parse selected cities, using default search locations")
                selected_cities = []
        
        # Use selected cities if provided, otherwise use default comprehensive coverage
        if selected_cities:
            # Convert selected cities to search locations with 200km radius
            search_locations = [(city, 200000) for city in selected_cities]
            logger.info(f"Searching {len(selected_cities)} selected cities")
        else:
            # Search for stores across the US using comprehensive city coverage
            # This ensures complete coverage by searching around major cities in each state
            search_locations = [
            # Alabama
            ("Birmingham, AL", 200000), ("Montgomery, AL", 200000), ("Mobile, AL", 200000), ("Huntsville, AL", 200000),
            # Alaska  
            ("Anchorage, AK", 300000), ("Fairbanks, AK", 300000), ("Juneau, AK", 200000),
            # Arizona
            ("Phoenix, AZ", 200000), ("Tucson, AZ", 200000), ("Mesa, AZ", 200000), ("Chandler, AZ", 200000),
            # Arkansas
            ("Little Rock, AR", 200000), ("Fort Smith, AR", 200000), ("Fayetteville, AR", 200000),
            # California
            ("Los Angeles, CA", 200000), ("San Diego, CA", 200000), ("San Jose, CA", 200000), ("San Francisco, CA", 200000),
            ("Fresno, CA", 200000), ("Sacramento, CA", 200000), ("Long Beach, CA", 200000), ("Oakland, CA", 200000),
            ("Bakersfield, CA", 200000), ("Anaheim, CA", 200000), ("Santa Ana, CA", 200000), ("Riverside, CA", 200000),
            # Colorado
            ("Denver, CO", 200000), ("Colorado Springs, CO", 200000), ("Aurora, CO", 200000), ("Fort Collins, CO", 200000),
            # Connecticut
            ("Bridgeport, CT", 200000), ("New Haven, CT", 200000), ("Hartford, CT", 200000), ("Stamford, CT", 200000),
            # Delaware
            ("Wilmington, DE", 200000), ("Dover, DE", 200000),
            # Florida
            ("Jacksonville, FL", 200000), ("Miami, FL", 200000), ("Tampa, FL", 200000), ("Orlando, FL", 200000),
            ("St. Petersburg, FL", 200000), ("Hialeah, FL", 200000), ("Tallahassee, FL", 200000), ("Fort Lauderdale, FL", 200000),
            ("Port St. Lucie, FL", 200000), ("Cape Coral, FL", 200000), ("Pembroke Pines, FL", 200000), ("Hollywood, FL", 200000),
            # Georgia
            ("Atlanta, GA", 200000), ("Augusta, GA", 200000), ("Columbus, GA", 200000), ("Savannah, GA", 200000),
            ("Athens, GA", 200000), ("Sandy Springs, GA", 200000), ("Roswell, GA", 200000), ("Macon, GA", 200000),
            # Hawaii
            ("Honolulu, HI", 200000), ("Pearl City, HI", 200000), ("Hilo, HI", 200000),
            # Idaho
            ("Boise, ID", 200000), ("Nampa, ID", 200000), ("Meridian, ID", 200000), ("Idaho Falls, ID", 200000),
            # Illinois
            ("Chicago, IL", 200000), ("Aurora, IL", 200000), ("Rockford, IL", 200000), ("Joliet, IL", 200000),
            ("Naperville, IL", 200000), ("Springfield, IL", 200000), ("Peoria, IL", 200000), ("Elgin, IL", 200000),
            # Indiana
            ("Indianapolis, IN", 200000), ("Fort Wayne, IN", 200000), ("Evansville, IN", 200000), ("South Bend, IN", 200000),
            ("Carmel, IN", 200000), ("Fishers, IN", 200000), ("Bloomington, IN", 200000), ("Hammond, IN", 200000),
            # Iowa
            ("Des Moines, IA", 200000), ("Cedar Rapids, IA", 200000), ("Davenport, IA", 200000), ("Sioux City, IA", 200000),
            # Kansas
            ("Wichita, KS", 200000), ("Overland Park, KS", 200000), ("Kansas City, KS", 200000), ("Topeka, KS", 200000),
            # Kentucky
            ("Louisville, KY", 200000), ("Lexington, KY", 200000), ("Bowling Green, KY", 200000), ("Owensboro, KY", 200000),
            # Louisiana
            ("New Orleans, LA", 200000), ("Baton Rouge, LA", 200000), ("Shreveport, LA", 200000), ("Lafayette, LA", 200000),
            ("Lake Charles, LA", 200000), ("Kenner, LA", 200000), ("Bossier City, LA", 200000), ("Monroe, LA", 200000),
            # Maine
            ("Portland, ME", 200000), ("Lewiston, ME", 200000), ("Bangor, ME", 200000), ("South Portland, ME", 200000),
            # Maryland
            ("Baltimore, MD", 200000), ("Frederick, MD", 200000), ("Rockville, MD", 200000), ("Gaithersburg, MD", 200000),
            ("Bowie, MD", 200000), ("Hagerstown, MD", 200000), ("Annapolis, MD", 200000),
            # Massachusetts
            ("Boston, MA", 200000), ("Worcester, MA", 200000), ("Springfield, MA", 200000), ("Cambridge, MA", 200000),
            ("Lowell, MA", 200000), ("Brockton, MA", 200000), ("New Bedford, MA", 200000), ("Quincy, MA", 200000),
            # Michigan
            ("Detroit, MI", 200000), ("Grand Rapids, MI", 200000), ("Warren, MI", 200000), ("Sterling Heights, MI", 200000),
            ("Lansing, MI", 200000), ("Ann Arbor, MI", 200000), ("Flint, MI", 200000), ("Dearborn, MI", 200000),
            # Minnesota
            ("Minneapolis, MN", 200000), ("Saint Paul, MN", 200000), ("Rochester, MN", 200000), ("Duluth, MN", 200000),
            ("Bloomington, MN", 200000), ("Brooklyn Park, MN", 200000), ("Plymouth, MN", 200000), ("St. Cloud, MN", 200000),
            # Mississippi
            ("Jackson, MS", 200000), ("Gulfport, MS", 200000), ("Southaven, MS", 200000), ("Hattiesburg, MS", 200000),
            # Missouri
            ("Kansas City, MO", 200000), ("Saint Louis, MO", 200000), ("Springfield, MO", 200000), ("Independence, MO", 200000),
            ("Columbia, MO", 200000), ("Lee's Summit, MO", 200000), ("O'Fallon, MO", 200000), ("St. Joseph, MO", 200000),
            # Montana
            ("Billings, MT", 200000), ("Missoula, MT", 200000), ("Great Falls, MT", 200000), ("Bozeman, MT", 200000),
            # Nebraska
            ("Omaha, NE", 200000), ("Lincoln, NE", 200000), ("Bellevue, NE", 200000), ("Grand Island, NE", 200000),
            # Nevada
            ("Las Vegas, NV", 200000), ("Henderson, NV", 200000), ("Reno, NV", 200000), ("North Las Vegas, NV", 200000),
            ("Sparks, NV", 200000), ("Carson City, NV", 200000),
            # New Hampshire
            ("Manchester, NH", 200000), ("Nashua, NH", 200000), ("Concord, NH", 200000), ("Derry, NH", 200000),
            # New Jersey
            ("Newark, NJ", 200000), ("Jersey City, NJ", 200000), ("Paterson, NJ", 200000), ("Elizabeth, NJ", 200000),
            ("Edison, NJ", 200000), ("Woodbridge, NJ", 200000), ("Lakewood, NJ", 200000), ("Toms River, NJ", 200000),
            # New Mexico
            ("Albuquerque, NM", 200000), ("Las Cruces, NM", 200000), ("Rio Rancho, NM", 200000), ("Santa Fe, NM", 200000),
            # New York
            ("New York, NY", 200000), ("Buffalo, NY", 200000), ("Rochester, NY", 200000), ("Yonkers, NY", 200000),
            ("Syracuse, NY", 200000), ("Albany, NY", 200000), ("New Rochelle, NY", 200000), ("Mount Vernon, NY", 200000),
            ("Schenectady, NY", 200000), ("Utica, NY", 200000), ("White Plains, NY", 200000), ("Hempstead, NY", 200000),
            # North Carolina
            ("Charlotte, NC", 200000), ("Raleigh, NC", 200000), ("Greensboro, NC", 200000), ("Durham, NC", 200000),
            ("Winston-Salem, NC", 200000), ("Fayetteville, NC", 200000), ("Cary, NC", 200000), ("Wilmington, NC", 200000),
            # North Dakota
            ("Fargo, ND", 200000), ("Bismarck, ND", 200000), ("Grand Forks, ND", 200000), ("Minot, ND", 200000),
            # Ohio
            ("Columbus, OH", 200000), ("Cleveland, OH", 200000), ("Cincinnati, OH", 200000), ("Toledo, OH", 200000),
            ("Akron, OH", 200000), ("Dayton, OH", 200000), ("Parma, OH", 200000), ("Canton, OH", 200000),
            ("Youngstown, OH", 200000), ("Lorain, OH", 200000), ("Hamilton, OH", 200000), ("Springfield, OH", 200000),
            # Oklahoma
            ("Oklahoma City, OK", 200000), ("Tulsa, OK", 200000), ("Norman, OK", 200000), ("Broken Arrow, OK", 200000),
            # Oregon
            ("Portland, OR", 200000), ("Salem, OR", 200000), ("Eugene, OR", 200000), ("Gresham, OR", 200000),
            ("Hillsboro, OR", 200000), ("Bend, OR", 200000), ("Medford, OR", 200000), ("Springfield, OR", 200000),
            # Pennsylvania
            ("Philadelphia, PA", 200000), ("Pittsburgh, PA", 200000), ("Allentown, PA", 200000), ("Erie, PA", 200000),
            ("Reading, PA", 200000), ("Scranton, PA", 200000), ("Bethlehem, PA", 200000), ("Lancaster, PA", 200000),
            ("Harrisburg, PA", 200000), ("Altoona, PA", 200000), ("York, PA", 200000), ("State College, PA", 200000),
            # Rhode Island
            ("Providence, RI", 200000), ("Warwick, RI", 200000), ("Cranston, RI", 200000), ("Pawtucket, RI", 200000),
            # South Carolina
            ("Columbia, SC", 200000), ("Charleston, SC", 200000), ("North Charleston, SC", 200000), ("Mount Pleasant, SC", 200000),
            ("Rock Hill, SC", 200000), ("Greenville, SC", 200000), ("Summerville, SC", 200000), ("Sumter, SC", 200000),
            # South Dakota
            ("Sioux Falls, SD", 200000), ("Rapid City, SD", 200000), ("Aberdeen, SD", 200000), ("Brookings, SD", 200000),
            # Tennessee
            ("Nashville, TN", 200000), ("Memphis, TN", 200000), ("Knoxville, TN", 200000), ("Chattanooga, TN", 200000),
            ("Clarksville, TN", 200000), ("Murfreesboro, TN", 200000), ("Franklin, TN", 200000), ("Jackson, TN", 200000),
            # Texas
            ("Houston, TX", 200000), ("San Antonio, TX", 200000), ("Dallas, TX", 200000), ("Austin, TX", 200000),
            ("Fort Worth, TX", 200000), ("El Paso, TX", 200000), ("Arlington, TX", 200000), ("Corpus Christi, TX", 200000),
            ("Plano, TX", 200000), ("Lubbock, TX", 200000), ("Laredo, TX", 200000), ("Garland, TX", 200000),
            ("Irving, TX", 200000), ("Amarillo, TX", 200000), ("Grand Prairie, TX", 200000), ("Brownsville, TX", 200000),
            ("Pasadena, TX", 200000), ("Mesquite, TX", 200000), ("McKinney, TX", 200000), ("McAllen, TX", 200000),
            # Utah
            ("Salt Lake City, UT", 200000), ("West Valley City, UT", 200000), ("Provo, UT", 200000), ("West Jordan, UT", 200000),
            ("Orem, UT", 200000), ("Sandy, UT", 200000), ("Ogden, UT", 200000), ("St. George, UT", 200000),
            # Vermont
            ("Burlington, VT", 200000), ("Essex, VT", 200000), ("South Burlington, VT", 200000), ("Colchester, VT", 200000),
            # Virginia
            ("Virginia Beach, VA", 200000), ("Norfolk, VA", 200000), ("Chesapeake, VA", 200000), ("Richmond, VA", 200000),
            ("Newport News, VA", 200000), ("Alexandria, VA", 200000), ("Hampton, VA", 200000), ("Portsmouth, VA", 200000),
            ("Suffolk, VA", 200000), ("Roanoke, VA", 200000), ("Lynchburg, VA", 200000), ("Harrisonburg, VA", 200000),
            # Washington
            ("Seattle, WA", 200000), ("Spokane, WA", 200000), ("Tacoma, WA", 200000), ("Vancouver, WA", 200000),
            ("Bellevue, WA", 200000), ("Everett, WA", 200000), ("Kent, WA", 200000), ("Renton, WA", 200000),
            ("Yakima, WA", 200000), ("Federal Way, WA", 200000), ("Spokane Valley, WA", 200000), ("Bellingham, WA", 200000),
            # West Virginia
            ("Charleston, WV", 200000), ("Huntington, WV", 200000), ("Parkersburg, WV", 200000), ("Morgantown, WV", 200000),
            # Wisconsin
            ("Milwaukee, WI", 200000), ("Madison, WI", 200000), ("Green Bay, WI", 200000), ("Kenosha, WI", 200000),
            ("Racine, WI", 200000), ("Appleton, WI", 200000), ("Waukesha, WI", 200000), ("Oshkosh, WI", 200000),
            # Wyoming
            ("Cheyenne, WY", 200000), ("Casper, WY", 200000), ("Laramie, WY", 200000), ("Gillette, WY", 200000),
            # Washington DC
            ("Washington, DC", 200000)
            ]
            logger.info(f"Using default comprehensive search across {len(search_locations)} major US cities")
        
        all_stores = []
        seen_place_ids = set()
        retailer_results = {}
        
        # Calculate total searches needed
        total_searches = len(retailer_names) * len(search_locations)
        current_search = 0
        
        logger.info(f"Searching for {len(retailer_names)} retailers across {len(search_locations)} locations")
        
        # Clear any previous search results
        if selected_cities:
            if len(retailer_names) == 1:
                flash(f'Starting search for "{retailer_names[0]}" in {len(selected_cities)} selected cities...', 'info')
            else:
                flash(f'Starting search for {len(retailer_names)} retailers in {len(selected_cities)} selected cities...', 'info')
        else:
            if len(retailer_names) == 1:
                flash(f'Starting comprehensive search for "{retailer_names[0]}" across all US cities...', 'info')
            else:
                flash(f'Starting comprehensive search for {len(retailer_names)} retailers across all US cities...', 'info')
        
        # Cost tracking
        api_calls_made = 0
        max_api_calls = 200  # Increased limit for multiple retailers
        
        # Search each retailer
        for retailer_name in retailer_names:
            retailer_stores = []
            logger.info(f"Searching for {retailer_name} stores...")
            
            for location, radius in search_locations:
                if api_calls_made >= max_api_calls:
                    logger.warning(f"Reached maximum API calls limit ({max_api_calls}). Stopping search to prevent excessive charges.")
                    break
                    
                current_search += 1
                try:
                    stores = search_retailer_stores(retailer_name, location, radius)
                    api_calls_made += 1  # Count each search as an API call
                    
                    # Get ALL stores, no limits
                    for store in stores:
                        # Avoid duplicates by checking place_id
                        if store['place_id'] not in seen_place_ids:
                            # Parse address components from formatted_address
                            formatted_addr = store.get('formatted_address', store.get('address', ''))
                            street_address, city, state, zip_code = _parse_address_components(formatted_addr)
                            
                            # Ensure all fields have proper default values to avoid JSON serialization issues
                            clean_store = {
                                'name': store.get('name', ''),
                                'address': street_address,  # Use parsed street address instead of full address
                                'formatted_address': formatted_addr,
                                'city': city,
                                'state': state,
                                'zip_code': zip_code,
                                'rating': store.get('rating', 0),
                                'user_ratings_total': store.get('user_ratings_total', 0),
                                'place_id': store.get('place_id', ''),
                                'latitude': store.get('latitude', 0),
                                'longitude': store.get('longitude', 0),
                                'types': list(store.get('types', [])),
                                'business_status': store.get('business_status', ''),
                                'price_level': store.get('price_level', 0),
                                'phone_number': store.get('phone_number', ''),
                                'website': store.get('website', ''),
                                'opening_hours': str(store.get('opening_hours', {})),
                                'retailer_name': retailer_name  # Use search term as retailer name
                            }
                            all_stores.append(clean_store)
                            retailer_stores.append(clean_store)
                            seen_place_ids.add(store['place_id'])
                        
                except Exception as e:
                    logger.warning(f"Error searching for {retailer_name} in {location}: {e}")
                    continue
            
            # Store results for this retailer
            retailer_results[retailer_name] = {
                'stores': retailer_stores,
                'count': len(retailer_stores)
            }
        
        if not all_stores:
            if len(retailer_names) == 1:
                flash(f'No stores found for "{retailer_names[0]}" across the United States', 'warning')
            else:
                flash(f'No stores found for any of the {len(retailer_names)} retailers across the United States', 'warning')
            return redirect(url_for('index'))
        
        # Sort stores by retailer name, then by address for better organization
        all_stores.sort(key=lambda x: (x.get('retailer_name', ''), x.get('formatted_address', x.get('address', ''))))

        # Group stores by official retailer name for breakdown display
        official_retailer_results = {}
        for store in all_stores:
            official_name = store.get('retailer_name', 'Unknown')
            if official_name not in official_retailer_results:
                official_retailer_results[official_name] = {
                    'stores': [],
                    'count': 0
                }
            official_retailer_results[official_name]['stores'].append(store)
            official_retailer_results[official_name]['count'] += 1

        # Clear previous cache and create new one
        _cleanup_cache()
        # Remove current session's cache key if it exists
        old_cache_key = session.get('last_results_key')
        if old_cache_key and old_cache_key in LAST_RESULTS_CACHE:
            LAST_RESULTS_CACHE.pop(old_cache_key, None)
        
        cache_key = str(uuid.uuid4())
        
        # Create display name for multiple retailers
        if len(retailer_names) == 1:
            display_name = retailer_names[0]
        else:
            display_name = f"{len(retailer_names)} Retailers"
        
        LAST_RESULTS_CACHE[cache_key] = {
            'retailer_name': display_name,
            'retailer_names': retailer_names,
            'retailer_results': retailer_results,
            'official_retailer_results': official_retailer_results,
            'total_found': len(all_stores),
            'stores': all_stores,
            'api_calls_made': api_calls_made,
            'ts': datetime.utcnow().timestamp()
        }
        session['last_results_key'] = cache_key
        session['last_search_terms'] = retailer_input
        
        return render_template('simple_results.html', 
                             stores=all_stores,
                             results=all_stores,  # Add this line - template expects 'results' variable
                             retailer_name=display_name,
                             retailer_names=retailer_names or [],
                             retailer_results=retailer_results or {},
                             official_retailer_results=official_retailer_results or {},
                             total_found=len(all_stores),
                             api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '',
                             api_calls_made=api_calls_made,
                             estimated_cost=api_calls_made * 0.032)  # $0.032 per Places API call
        
    except Exception as e:
        logger.error(f"Error in search_stores: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for programmatic access."""
    try:
        data = request.get_json()
        retailer_name = data.get('retailer_name', '').strip()
        location = data.get('location', 'United States').strip()
        radius = data.get('radius', 50000)
        
        if not retailer_name:
            return jsonify({'error': 'retailer_name is required'}), 400
        
        google_stores = search_retailer_stores(retailer_name, location, radius)
        
        return jsonify({
            'retailer_name': retailer_name,
            'location': location,
            'radius': radius,
            'stores_found': len(google_stores),
            'stores': google_stores
        })
        
    except Exception as e:
        logger.error(f"Error in API search: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/billing', methods=['GET'])
def api_billing():
    """API endpoint to get real-time billing data."""
    try:
        billing_data = get_google_cloud_billing_data()
        if billing_data:
            return jsonify(billing_data)
        else:
            return jsonify({'error': 'Unable to fetch billing data'}), 500
    except Exception as e:
        logger.error(f"Error getting billing data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/results')
def view_results():
    """Show last search results from in-memory cache via session key."""
    cache_key = session.get('last_results_key')
    cached = LAST_RESULTS_CACHE.get(cache_key) if cache_key else None
    
    if not cached:
        # Show empty results page with CSV upload option
        return render_template('simple_results.html',
                               stores=[],
                               results=[],
                               retailer_name='Results',
                               total_found=0,
                               api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '',
                               api_calls_made=0,
                               estimated_cost=0)

    # Debug logging
    logger.info(f"Cache key: {cache_key}")
    logger.info(f"Cached data keys: {cached.keys() if cached else 'None'}")
    logger.info(f"Number of stores: {len(cached.get('stores', []))}")
    
    return render_template('simple_results.html',
                           stores=cached.get('stores', []),
                           results=cached.get('stores', []),
                           retailer_name=cached.get('retailer_name', 'Results'),
                           retailer_names=cached.get('retailer_names', []),
                           retailer_results=cached.get('retailer_results', {}),
                           official_retailer_results=cached.get('official_retailer_results', {}),
                           total_found=cached.get('total_found', 0),
                           api_key=os.getenv('GOOGLE_MAPS_API_KEY') or '',
                           api_calls_made=cached.get('api_calls_made', 0),
                           estimated_cost=cached.get('api_calls_made', 0) * 0.032)

@app.route('/save-to-database', methods=['POST'])
def save_to_database():
    """Save search results to the retailer database."""
    try:
        data = request.get_json()
        retailer_name = data.get('retailer_name')
        stores = data.get('stores', [])
        
        if not retailer_name or not stores:
            return jsonify({'success': False, 'error': 'Missing retailer name or stores data'})
        
        # Filter out permanently closed stores
        active_stores = []
        closed_count = 0
        
        for store in stores:
            business_status = store.get('business_status', '').lower()
            if business_status in ['permanently_closed', 'closed_permanently']:
                closed_count += 1
                continue
            active_stores.append(store)
        
        # Count unique cities
        unique_cities = set()
        for store in active_stores:
            city = store.get('city', '').strip()
            if city:
                unique_cities.add(city)
        
        # Load existing database
        retailer_data = _load_db()
        logger.info(f"Loaded {len(retailer_data)} existing retailers from database")
        
        # Add the new retailer data
        retailer_entry = {
            'retailer_name': retailer_name,
            'stores': active_stores,
            'total_stores': len(active_stores),
            'total_cities': len(unique_cities),
            'date_added': datetime.now().isoformat()
        }
        
        retailer_data.append(retailer_entry)
        _save_db(retailer_data)
        
        message = f'Successfully saved {len(active_stores)} active stores for {retailer_name}'
        if closed_count > 0:
            message += f' (excluded {closed_count} permanently closed stores)'
        if len(unique_cities) > 0:
            message += f' across {len(unique_cities)} unique cities'
        
        logger.info(f"Saved retailer '{retailer_name}' with {len(active_stores)} active stores across {len(unique_cities)} cities")
        
        return jsonify({
            'success': True, 
            'message': message,
            'total_retailers': len(retailer_data),
            'active_stores': len(active_stores),
            'closed_stores_excluded': closed_count,
            'unique_cities': len(unique_cities)
        })
        
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/clear-database', methods=['POST'])
def clear_database():
    """Clear the retailer database (for testing purposes)."""
    try:
        _save_db([])
        logger.info("Retailer database cleared")
        return jsonify({'success': True, 'message': 'Database cleared successfully'})
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/remove-retailer', methods=['POST'])
def remove_retailer():
    """Remove a retailer from the database (mark as removed but keep data)."""
    try:
        data = request.get_json()
        retailer_index = data.get('retailer_index')
        
        if retailer_index is None:
            return jsonify({'success': False, 'error': 'Missing retailer index'})
        
        # Load existing database
        retailer_data = _load_db()
        
        if retailer_index < 0 or retailer_index >= len(retailer_data):
            return jsonify({'success': False, 'error': 'Invalid retailer index'})
        
        # Mark retailer as removed
        retailer_data[retailer_index]['removed'] = True
        retailer_data[retailer_index]['removed_date'] = datetime.now().isoformat()
        
        # Save updated database
        _save_db(retailer_data)
        
        retailer_name = retailer_data[retailer_index].get('retailer_name', 'Unknown')
        logger.info(f"Removed retailer '{retailer_name}' from database")
        
        return jsonify({
            'success': True,
            'message': f'Successfully removed {retailer_name}',
            'remaining_retailers': len([r for r in retailer_data if not r.get('removed', False)])
        })
        
    except Exception as e:
        logger.error(f"Error removing retailer: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/restore-retailer', methods=['POST'])
def restore_retailer():
    """Restore a removed retailer to the database."""
    try:
        data = request.get_json()
        retailer_index = data.get('retailer_index')
        
        if retailer_index is None:
            return jsonify({'success': False, 'error': 'Missing retailer index'})
        
        # Load existing database
        retailer_data = _load_db()
        
        if retailer_index < 0 or retailer_index >= len(retailer_data):
            return jsonify({'success': False, 'error': 'Invalid retailer index'})
        
        # Restore retailer
        retailer_data[retailer_index]['removed'] = False
        if 'removed_date' in retailer_data[retailer_index]:
            del retailer_data[retailer_index]['removed_date']
        
        # Save updated database
        _save_db(retailer_data)
        
        retailer_name = retailer_data[retailer_index].get('retailer_name', 'Unknown')
        logger.info(f"Restored retailer '{retailer_name}' to database")
        
        return jsonify({
            'success': True,
            'message': f'Successfully restored {retailer_name}',
            'remaining_retailers': len([r for r in retailer_data if not r.get('removed', False)])
        })
        
    except Exception as e:
        logger.error(f"Error restoring retailer: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete-retailer', methods=['POST'])
def delete_retailer():
    """Permanently delete a retailer from the database."""
    try:
        data = request.get_json()
        retailer_index = data.get('retailer_index')
        
        if retailer_index is None:
            return jsonify({'success': False, 'error': 'Missing retailer index'})
        
        # Load existing database
        retailer_data = _load_db()
        
        if retailer_index < 0 or retailer_index >= len(retailer_data):
            return jsonify({'success': False, 'error': 'Invalid retailer index'})
        
        # Get retailer name for logging
        retailer_name = retailer_data[retailer_index].get('retailer_name', 'Unknown')
        
        # Permanently remove the retailer
        deleted_retailer = retailer_data.pop(retailer_index)
        
        # Save updated database
        _save_db(retailer_data)
        
        logger.info(f"Permanently deleted retailer '{retailer_name}' with {deleted_retailer.get('total_stores', 0)} stores")
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {retailer_name}',
            'remaining_retailers': len(retailer_data)
        })
        
    except Exception as e:
        logger.error(f"Error deleting retailer: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/upload-results-csv', methods=['POST'])
def upload_results_csv():
    """Upload and process a CSV file of search results."""
    try:
        if 'csv_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['csv_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Only CSV files are allowed'})
        
        # Read the CSV file
        # Read CSV with ZIP code as string to preserve leading zeros
        df = pd.read_csv(file, dtype={'Zip': str, 'Zip Code': str})
        
        # Convert DataFrame to store format
        stores = []
        store_names = []
        
        for _, row in df.iterrows():
            # Handle both 'Lat'/'Long' and 'Latitude'/'Longitude' column names
            lat = row.get('Lat', row.get('Latitude', 0))
            lng = row.get('Long', row.get('Longitude', 0))
            
            store_name = str(row.get('Store Name', ''))
            store_names.append(store_name)
            
            store = {
                'name': store_name,
                'address': str(row.get('Address', '')),
                'phone_number': str(row.get('Phone', '')),
                'rating': row.get('Rating', ''),
                'website': str(row.get('Website', '')),
                'place_id': f"uploaded_{len(stores)}",  # Generate a placeholder ID
                'latitude': float(lat) if lat else 0,
                'longitude': float(lng) if lng else 0,
                'formatted_address': str(row.get('Address', '')),
                'business_status': str(row.get('Status', 'OPERATIONAL')),
                'city': str(row.get('City', '')),
                'state': str(row.get('State', '')),
                'zip_code': str(row.get('Zip', '')),
                'retailer_name': ''  # Will be set after analyzing store names
            }
            stores.append(store)
        
        # Use the search terms from the session if available, otherwise default
        search_terms = session.get('last_search_terms', 'Uploaded Results')
        for store in stores:
            store['retailer_name'] = search_terms
        
        # Store in session cache
        cache_key = str(uuid.uuid4())
        LAST_RESULTS_CACHE[cache_key] = {
            'stores': stores,
            'retailer_name': search_terms,
            'total_found': len(stores),
            'api_calls_made': 0,
            'timestamp': datetime.now()
        }
        session['last_results_key'] = cache_key
        session.modified = True
        
        # Debug logging
        logger.info(f"CSV Upload - Cache key created: {cache_key}")
        logger.info(f"CSV Upload - Number of stores processed: {len(stores)}")
        logger.info(f"CSV Upload - Session key set: {session.get('last_results_key')}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {len(stores)} stores from CSV',
            'total_stores': len(stores)
        })
        
    except Exception as e:
        logger.error(f"Error uploading results CSV: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/bulk-upload-retailers', methods=['POST'])
def bulk_upload_retailers():
    """Handle bulk CSV upload for retailer database."""
    try:
        files = request.files.getlist('csv_files')
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({'success': False, 'error': 'No files selected'})
        
        uploaded_files = []
        
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                try:
                    # Read CSV file
                    df = pd.read_csv(filepath)
                    
                    # Process the CSV data (similar to existing CSV upload logic)
                    stores = []
                    for _, row in df.iterrows():
                        # Extract store information from CSV
                        store = {
                            'name': str(row.get('Store Name', row.get('Name', ''))),
                            'address': str(row.get('Address', '')),
                            'city': str(row.get('City', '')),
                            'state': str(row.get('State', '')),
                            'zip_code': str(row.get('ZIP', row.get('Zip', ''))),
                            'phone_number': str(row.get('Phone', '')),
                            'rating': float(row.get('Rating', 0)) if row.get('Rating') else 0,
                            'website': str(row.get('Website', '')),
                            'latitude': float(row.get('Latitude', 0)) if row.get('Latitude') else 0,
                            'longitude': float(row.get('Longitude', 0)) if row.get('Longitude') else 0,
                            'formatted_address': str(row.get('Address', '')),
                            'business_status': 'OPERATIONAL',
                            'retailer_name': filename.replace('.csv', '').replace('_', ' ').title()
                        }
                        stores.append(store)
                    
                    # Filter out permanently closed stores
                    active_stores = []
                    closed_count = 0
                    
                    for store in stores:
                        business_status = store.get('business_status', '').lower()
                        if business_status in ['permanently_closed', 'closed_permanently']:
                            closed_count += 1
                            continue
                        active_stores.append(store)
                    
                    # Count unique cities
                    unique_cities = set()
                    for store in active_stores:
                        city = store.get('city', '').strip()
                        if city:
                            unique_cities.add(city)
                    
                    # Create retailer entry
                    retailer_entry = {
                        'retailer_name': store['retailer_name'],
                        'stores': active_stores,
                        'total_stores': len(active_stores),
                        'total_cities': len(unique_cities),
                        'date_added': datetime.now().isoformat(),
                        'source': 'csv_upload',
                        'filename': filename,
                        'removed': False
                    }
                    
                    # Save to database
                    all_retailer_data = _load_db()
                    all_retailer_data.append(retailer_entry)
                    _save_db(all_retailer_data)
                    
                    uploaded_files.append({
                        'filename': filename,
                        'upload_date': datetime.now().isoformat(),
                        'status': 'success',
                        'stores_count': len(stores),
                        'retailer_name': store['retailer_name']
                    })
                    
                    logger.info(f"Successfully processed CSV file: {filename} with {len(stores)} stores")
                    
                except Exception as e:
                    logger.error(f"Error processing CSV file {filename}: {e}")
                    uploaded_files.append({
                        'filename': filename,
                        'upload_date': datetime.now().isoformat(),
                        'status': 'error',
                        'error': str(e)
                    })
                finally:
                    # Clean up uploaded file
                    if os.path.exists(filepath):
                        os.remove(filepath)
            else:
                uploaded_files.append({
                    'filename': file.filename if file else 'unknown',
                    'upload_date': datetime.now().isoformat(),
                    'status': 'error',
                    'error': 'Invalid file type or empty file'
                })
        
        return jsonify({
            'success': True,
            'uploaded_files': uploaded_files,
            'total_files': len(uploaded_files)
        })
        
    except Exception as e:
        logger.error(f"Error in bulk upload: {e}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # Check if API key is configured
    if not os.getenv('GOOGLE_MAPS_API_KEY'):
        print("Warning: GOOGLE_MAPS_API_KEY not found in environment variables.")
        print("Please create a .env file with your Google Maps API key.")
    
    # Allow overriding the port via environment variable PORT
    try:
        port = int(os.getenv('PORT', '5002'))
    except ValueError:
        port = 5002

    app.run(debug=True, host='0.0.0.0', port=port)

