import os
import sys
import chromadb
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# 1. PATH CONFIGURATION FOR YOUR ARCHITECTURE
# Points directly to: sentinel_project/processing/vector_indexing/
current_dir = os.path.dirname(os.path.abspath(__file__)) 

# Saves chroma folder directly inside vector_indexing/
vector_folder = os.path.join(current_dir, 'chroma_storage')

# Step up two levels to find the .env file in the root project directory
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)
load_dotenv(os.path.join(project_root, '.env'))

from db_helper import get_db_connection


print(f" Attaching to Local ChromaDB Instance path: {vector_folder}")
chroma_client = chromadb.PersistentClient(path=vector_folder)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection(name="regional_safety_vectors")

def synchronize_vectors():
    print(" Mapping Database Signals to Dense Spatial Vectors...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Updated to extract s.location_id directly from the database rows
    query = """
        SELECT s.id, s.title, m.location_name, s.category, s.is_relevant, s.is_regional, s.location_id 
        FROM safety_signals s
        INNER JOIN monitoring_targets m ON s.location_id = m.id
        WHERE s.category != 'Unclassified'
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print(" Vectors clear: No source records extracted from MySQL.")
        cursor.close()
        conn.close()
        return
        
    ids = []
    documents = []
    metadatas = []
    
    for row in rows:
        row_id, title, loc_name, cat, rel, reg, loc_id = row
        ids.append(f"signal_{row_id}")
        documents.append(title)
        
        # Updated to pass the crucial numerical filter key
        metadatas.append({
            "location_id": int(loc_id),
            "location_name": str(loc_name),
            "category": str(cat),
            "is_relevant": int(rel if rel is not None else 1),
            "is_regional": int(reg if reg is not None else 0)
        })
        
    print(f" Encoding in batches...")
    embeddings = embedding_model.encode(documents, batch_size=32, show_progress_bar=True).tolist()
    
    # Overwrites the old metadata-less structure completely
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    cursor.close()
    conn.close()
    print(f" ChromaDB Semantic Vector Storage Completely Synced. Current Count: {collection.count()}")

if __name__ == "__main__":
    synchronize_vectors()