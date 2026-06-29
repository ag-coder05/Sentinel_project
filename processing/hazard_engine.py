import os
import logging
import sys
import streamlit as st

from sentence_transformers import SentenceTransformer

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
from utils import get_safe_secret
from pinecone import Pinecone
# Silence logs
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
logging.getLogger("transformers").setLevel(logging.ERROR)


# 1. CACHED PINECONE INITIALIZATION
@st.cache_resource
def get_pinecone_index():
    """Initializes and returns the Pinecone index object once."""
    api_key = get_safe_secret("PINECONE_API_KEY")
    host = get_safe_secret("PINECONE_HOST")
    return Pinecone(api_key=api_key).Index(host=host)

# 2. CACHED MODEL LOADING
_embedding_model = None
def get_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

def get_cached_metrics(city_name, cursor):
    query = """
        SELECT current_hazard_index, severity_tier, active_signals_count, 
               trajectory, primary_threat_distribution, tactical_action_steps 
        FROM predicted_safety_scores 
        WHERE location_id = (SELECT id FROM monitoring_targets WHERE location_name = %s LIMIT 1)
    """
    cursor.execute(query, (city_name,))
    return cursor.fetchone()

def semantic_archive_search(query_text, location_id, cursor, limit=3):
    model = get_model()
    index = get_pinecone_index()  # Call the cached function here
    
    try:
        query_vector = model.encode([query_text]).tolist()[0]
        
        # Pinecone query
        search_results = index.query(
            vector=query_vector,
            top_k=limit,
            filter={"location_id": {"$eq": int(location_id)}},
            include_metadata=True
        )
        
        formatted_results = []
        if search_results and 'matches' in search_results:
            for match in search_results['matches']:
                formatted_results.append({
                    "document": match.get('metadata', {}).get('title', 'No Title'),
                    "metadata": match.get('metadata', {}),
                    "score": match.get('score', 0.0)
                })
        return formatted_results

    except Exception as e:
        print(f"❌ Core Pinecone Query Exception: {e}")
        return []