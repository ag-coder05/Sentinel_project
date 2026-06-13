import os
import math
import mysql.connector
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from google import genai  # Standardized modern SDK
from sklearn.ensemble import RandomForestRegressor

# Load environment configurations explicitly from your local .env file
load_dotenv()

def run_predictive_analytics():
    # Initialize the modern, unified Gemini Client
    ai_client = genai.Client() # Automatically reads GEMINI_API_KEY from .env
    
    db_host = os.getenv("DB_HOST", "localhost")
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD") 
    db_name = os.getenv("DB_NAME", "sentinel_project")

    # Establish clean database connectivity
    conn = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name
    )
    cursor = conn.cursor(dictionary=True)

    print("🔄 Fetching target deployment locations...")
    cursor.execute("SELECT id, location_name FROM monitoring_targets")
    cities = cursor.fetchall()

    # TRAIN MATHEMATICAL DECAY FORECASTER
    X_train = np.array([[0], [12], [24], [48], [72], [168]])
    y_train = np.array([1.0, 0.78, 0.62, 0.38, 0.24, 0.05])

    # Named 'ml_model' to completely isolate it from the AI namespace
    ml_model = RandomForestRegressor(n_estimators=50, random_state=42)
    ml_model.fit(X_train, y_train)

    now = datetime.now()

    for city in cities:
        city_id = city['id']
        city_name = city['location_name']
        print(f"📊 Running math models and cloud AI analytics for {city_name}...")

        cursor.execute("""
            SELECT sentiment_negative, timestamp, category, title 
            FROM safety_signals 
            WHERE location_id = %s AND is_relevant = 1
        """, (city_id,))
        signals = cursor.fetchall()

        active_count = len(signals)
        if active_count == 0:
            print(f"➖ Zero active signals processed for {city_name}. Skipping profile.")
            continue

        total_weighted_severity = 0.0
        total_weight = 0.0
        headline_bullets = []

        for sig in signals:
            hours_elapsed = (now - sig['timestamp']).total_seconds() / 3600.0
            decay_weight = math.exp(-0.02 * max(0, hours_elapsed)) if hours_elapsed <= 168 else 0.05
            
            weighted_sentiment = float(sig['sentiment_negative']) * decay_weight
            total_weighted_severity += weighted_sentiment
            total_weight += decay_weight

            if len(headline_bullets) < 3:
                headline_bullets.append(f"- {sig['title']} [Category: {sig['category']}]")

        current_hazard_index = min(100.0, (total_weighted_severity * 10.0))

        if current_hazard_index < 30:
            severity_tier = "LOW"
        elif current_hazard_index < 60:
            severity_tier = "ELEVATED"
        else:
            severity_tier = "HIGH"

        # Safe prediction call onto your Scikit-Learn regressor object
        predicted_risk_12h = float(ml_model.predict([[12]])[0] * current_hazard_index)

        if predicted_risk_12h > current_hazard_index * 1.15:
            trajectory = "RISING"
        elif predicted_risk_12h < current_hazard_index * 0.85:
            trajectory = "FALLING"
        else:
            trajectory = "STABLE"

        headline_bullet_string = "\n".join(headline_bullets)
        prompt = f"""
        You are an expert humanitarian crisis analyst parsing security indices for an NGO dashboard deployment in {city_name}.
        Analyze these real breaking headlines driving a current hazard score of {current_hazard_index:.1f}/100:
        
        {headline_bullet_string}
        
        Generate exactly two distinct strings based ONLY on these real-world incidents. Do not include markdown headers or backticks.
        
        STRING 1 (Threat Summary): Provide a clean, plain English 2-sentence summary explaining how these specific issues are clashing or creating risk in the region.
        STRING 2 (Tactical Directives): Write exactly 2 brief, highly actionable bullet-pointed security instructions for field teams operating near these specific events. Separate the two lines with a normal newline.
        
        Separate your entire response into two parts using exactly this delimiter string: ---SPLIT---
        """

        try:
            # Modern, faster API syntax running the production 2.5-flash build
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            ai_output = response.text.strip().split('---SPLIT---')
            
            primary_threat_distribution = ai_output[0].strip()
            tactical_action_steps = ai_output[1].strip() if len(ai_output) > 1 else "1. Maintain baseline monitoring protocols."
        except Exception as e:
            print(f"⚠️ Gemini Cloud error, fallback activated: {e}")
            primary_threat_distribution = f"Continuous background signals tracking at volatility levels around {current_hazard_index:.1f}."
            tactical_action_steps = "1. Maintain baseline regional monitoring communication networks.\n2. Proceed with standard operational safety profiles."

        upsert_sql = """
            INSERT INTO predicted_safety_scores 
            (location_id, current_hazard_index, severity_tier, active_signals_count, 
             trajectory, primary_threat_distribution, tactical_action_steps, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                current_hazard_index = VALUES(current_hazard_index),
                severity_tier = VALUES(severity_tier),
                active_signals_count = VALUES(active_signals_count),
                trajectory = VALUES(trajectory),
                primary_threat_distribution = VALUES(primary_threat_distribution),
                tactical_action_steps = VALUES(tactical_action_steps),
                last_updated = NOW()
        """
        cursor.execute(upsert_sql, (
            city_id, current_hazard_index, severity_tier, active_count,
            trajectory, primary_threat_distribution, tactical_action_steps
        ))
        conn.commit()

    print("✅ Real-Time Analytical Matrices Cached Successfully into your true Schema!")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_predictive_analytics()