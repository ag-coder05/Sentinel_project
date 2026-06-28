import os
import logging
import chromadb
from sentence_transformers import SentenceTransformer

# Silence logs
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
logging.getLogger("transformers").setLevel(logging.ERROR)

# Setup path: relative to THIS file in the processing/ folder
current_dir = os.path.dirname(os.path.abspath(__file__))
vector_folder = os.path.join(current_dir, 'vector_indexing', 'chroma_storage')

print(f"📡 Hazard Engine connecting to vector space at: {vector_folder}")
chroma_client = chromadb.PersistentClient(path=vector_folder)
collection = chroma_client.get_or_create_collection(name="regional_safety_vectors")

# Lazy loading model
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
    try:
        query_vector = model.encode([query_text]).tolist()
        
        # Use $or to check both Int and String in one pass
        results = collection.query(
            query_embeddings=query_vector, 
            n_results=limit,
            where={"$or": [
                {"location_id": int(location_id)},
                {"location_id": str(location_id)}
            ]}
        )
        
        formatted_results = []
        if results and results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "document": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "score": results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
                })
        return formatted_results

    except Exception as e:
        print(f"❌ Core Vector Database Query Exception: {e}")
        return []