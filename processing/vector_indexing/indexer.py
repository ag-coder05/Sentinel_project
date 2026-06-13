import os
import mysql.connector
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
load_dotenv(os.path.join(project_root, '.env'))

db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME", "sentinel_db")
}

print(f" Attaching to Local ChromaDB Instance path: {vector_folder}")
chroma_client = chromadb.PersistentClient(path=vector_folder)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
collection = chroma_client.get_or_create_collection(name="regional_safety_vectors")

def synchronize_vectors():
    print(" Mapping Database Signals to Dense Spatial Vectors...")
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # Updated to extract s.location_id directly from the database rows
    query = """
        SELECT s.id, s.title, m.location_name, s.category, s.is_relevant, s.is_regional, s.location_id 
        FROM safety_signals s
        INNER JOIN monitoring_targets m ON s.location_id = m.id
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
        
    print(f" Encoding {len(documents)} elements with all-MiniLM-L6-v2 on local CPU...")
    embeddings = embedding_model.encode(documents).tolist()
    
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