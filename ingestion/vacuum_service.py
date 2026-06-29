import os
import sys
import time

from datetime import datetime

from dotenv import load_dotenv

# 1. Setup path to access root files
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# 2. Load Environment Variables from root .env
load_dotenv(os.path.join(project_root, '.env'))

# 3. Import your Helper and other libraries
from db_helper import get_db_connection
from gnews import GNews
from geopy.geocoders import Nominatim
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# 4. Initialize services
google_news = GNews(language='en', country='IN', period='14d')
geolocator = Nominatim(user_agent="sentinel_crisis_monitor")
analyzer = SentimentIntensityAnalyzer()

def run():
    print(" Initializing Dynamic Data Ingestion Pipeline...")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id, location_name, state, latitude, longitude FROM monitoring_targets")
    targets = cursor.fetchall()
    
    for target in targets:
        target_id = target['id']
        loc_name = target['location_name']
        state_name = target['state']
        lat = target['latitude']
        lon = target['longitude']
        
        # Spatial self-healing check
        if not lat or not lon:
            print(f" GPS parameters missing for {loc_name}. Geopy active...")
            try:
                spatial_data = geolocator.geocode(f"{loc_name}, {state_name}, India", timeout=10)
                if spatial_data:
                    lat, lon = spatial_data.latitude, spatial_data.longitude
                    cursor.execute(
                        "UPDATE monitoring_targets SET latitude = %s, longitude = %s WHERE id = %s",
                        (lat, lon, target_id)
                    )
                    conn.commit()
                time.sleep(1)
            except Exception as e:
                print(f" GeoPy Resolution Failed for {loc_name}: {e}")
                continue

        broad_search_query = (
            f"{loc_name} AND (safety OR emergency OR crisis OR accident OR fire OR "
            f"murder OR rape OR missing OR dead OR killed OR protest OR clash OR collapse OR flood)"
        )
        print(f" Sweeping GNews: '{broad_search_query}'")
        
        try:
            raw_feed = google_news.get_news(broad_search_query)
            inserted_count = 0
            
            for item in raw_feed:
                title = item['title']
                source = item['publisher']['title'] if isinstance(item['publisher'], dict) else item.get('publisher', 'Unknown')
                
                try:
                    clean_date = datetime.strptime(item['published date'], "%a, %d %b %Y %H:%M:%S %Z")
                    formatted_timestamp = clean_date.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    formatted_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                scores = analyzer.polarity_scores(title)
                compound_score = scores['compound']
                negative_score = scores['neg']
                
                insert_sql = """
                    INSERT IGNORE INTO safety_signals 
                    (title, source, timestamp, location_id, compound_score, sentiment_negative, category, is_relevant) 
                    VALUES (%s, %s, %s, %s, %s, %s, 'Unclassified', 1)
                """

                

                cursor.execute(insert_sql, (title, source, formatted_timestamp, target_id, compound_score, negative_score))
                if cursor.rowcount > 0:
                    inserted_count += 1
            
            conn.commit()
            print(f" Successfully cached {inserted_count} new unique signals for {loc_name}.\n")
            time.sleep(0.5)
            
        except Exception as e:
            print(f" Scraping operational fault for {loc_name}: {e}\n")
            
    cursor.close()
    conn.close()
    print(" Ingestion Layer Execution Concluded.")

if __name__ == "__main__":
    run()