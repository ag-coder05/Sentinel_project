import os
import json
import time
import sys
from google import genai  # Upgraded to the modern production SDK
from google.genai import types
import google.api_core.exceptions
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
load_dotenv(os.path.join(project_root, '.env'))

from db_helper import get_db_connection


# Unified client initialization (automatically pulls GEMINI_API_KEY from your .env)
ai_client = genai.Client()

def run_batch_refinery():
    print("🚀 Launching Context-Aware AI Classification Refinery...")
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Pull only what needs work
    cursor.execute("SELECT id, title FROM safety_signals WHERE category = 'Unclassified'")
    records = cursor.fetchall()
    
    if not records:
        print("✨ Clean check: All data points currently classified")
        cursor.close()
        conn.close()
        return

    batch_size = 10
    batches = [records[i:i + batch_size] for i in range(0, len(records), batch_size)]
    
    for b_idx, batch in enumerate(batches, 1):
        print(f"📦 [{b_idx}/{len(batches)}] Processing batch of {len(batch)} real headlines...")
        input_payload = [{"id": r["id"], "title": r["title"]} for r in batch]
        
        # HYBRID PROMPT: Combines your detailed guidelines with strict JSON enforcement
        prompt = f"""
        Analyze each news headline in this JSON array for an NGO safety dashboard focusing on regional hazards and human protection:
        {json.dumps(input_payload)}

        For each item, evaluate and return:
        1. "is_relevant": 1 if it's a genuine hazard, accident, crime, or crisis in India. 0 for PR, sports, celebrity appearance, promotional content, or normal political debates.
        2. "is_regional": 1 if it affects an entire state/sub-region (e.g., cyclones, state-wide floods, massive regional strikes/bandhs). 0 if city-specific, hyper-local, or neighborhood-bounded.
        3. "category": Choose the MOST accurate tag from this exact list:
            - 'Fire': Building blazes, factory fires, forest fires.
            - 'Accident': Train derailments, major vehicular pileups, plane crashes.
            - 'Protest': Bandhs, massive strikes, violent public rallies.
            - 'Disaster': Cyclones, major floods, earthquakes, heatwaves.
            - 'Infrastructure Failure': Bridge collapses, severe road cave-ins, long-term power grid failures.
            - 'Crime': Murders, thefts, major local law-and-order offenses.
            - 'Human Security Issue': Domestic abuse, violence against women/children, missing persons, human trafficking.
            - 'Irrelevant': Anything that does not pose a physical safety or immediate human protection risk.

        Output an array of JSON objects following this exact schema:
        [
          {{"id": 123, "is_relevant": 1, "is_regional": 0, "category": "Human Security Issue"}},
          ...
        ]
        """
        
        try:
            # Modern call layout using the 2.5-flash engine and structured output configuration
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            # Read clean text straight out of the modern API schema structure
            try:
                results = json.loads(response.text.strip())
            except json.JSONDecodeError:
                print(" Gemini returned invalid JSON. Skipping this batch.")
                time.sleep(5)
                continue # Skip to next batch
            
            update_sql = """
                UPDATE safety_signals 
                SET category = %s, is_relevant = %s, is_regional = %s 
                WHERE id = %s
            """
            for res in results:
                cursor.execute(update_sql, (res['category'], res['is_relevant'], res['is_regional'], res['id']))
            
            conn.commit()
            print(f"✅ Batch {b_idx} successfully saved and committed.")
            
            # Smart cooldown balance: 8.0 seconds protects free tier limits cleanly
            time.sleep(8.0)
            
        except google.api_core.exceptions.ResourceExhausted:
            print("⏳ Quota limit hit. Cool-down active for 65 seconds...")
            time.sleep(65)
        except Exception as e:
            print(f"❌ Batch {b_idx} processing error: {e}")
            time.sleep(5)

    cursor.close()
    conn.close()
    print("🏁 Context-Aware Classification processing completed safely.")

if __name__ == "__main__":
    run_batch_refinery()