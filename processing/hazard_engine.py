import os
import logging

# Force HuggingFace and Transformers to ignore missing multi-modal pathways and quiet down logs
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
logging.getLogger("transformers").setLevel(logging.ERROR)
import chromadb
from sentence_transformers import SentenceTransformer

# 1. SETUP EXACT MATCHING PATHS
current_dir = os.path.dirname(os.path.abspath(__file__)) # points to: processing/

# Dive straight down into your vector folder path
vector_folder = os.path.join(current_dir, 'vector_indexing', 'chroma_storage')

print(f"📡 Hazard Engine connecting to vector space at: {vector_folder}")
chroma_client = chromadb.PersistentClient(path=vector_folder)
collection = chroma_client.get_or_create_collection(name="regional_safety_vectors")

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def get_cached_metrics(city_name, cursor):
    """
    Fetches pre-calculated metrics directly from your database cache rows.
    Matches your exact MySQL schema column mappings.
    """
    query = """
        SELECT current_hazard_index, severity_tier, active_signals_count, 
               trajectory, primary_threat_distribution, tactical_action_steps 
        FROM predicted_safety_scores 
        WHERE location_id = (SELECT id FROM monitoring_targets WHERE location_name = %s LIMIT 1)
    """
    cursor.execute(query, (city_name,))
    return cursor.fetchone()


def semantic_archive_search(query_text, location_id, limit=3):
    """
    Queries your local persistent ChromaDB space for tracking historical trends.
    Defensively checks for both integer and string metadata matches.
    """
    try:
        # Generate the text embedding vector
        query_vector = embedding_model.encode([query_text]).tolist()
        
        # 1. First Attempt: Query matching it as an Integer (What your SQL uses)
        results = collection.query(
            query_embeddings=query_vector, 
            n_results=limit,
            where={"location_id": int(location_id)}
        )
        
        # If the integer query came up dry, immediately try checking as a String fallback
        if not results or not results['documents'] or len(results['documents'][0]) == 0:
            results = collection.query(
                query_embeddings=query_vector, 
                n_results=limit,
                where={"location_id": str(location_id)}  # Defensive String Conversion
            )
        
        formatted_results = []
        if results and results['documents'] and len(results['documents']) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "document": results['documents'][0][i],
                    "headline": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "score": results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
                })
        return formatted_results

    except Exception as e:
        print(f"❌ Core Vector Database Query Exception: {e}")
        return []