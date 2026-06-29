import os
import sys
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Path configuration
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

# Load .env from project root
load_dotenv(os.path.join(project_root, '.env'))

from db_helper import get_db_connection

# Initialize Pinecone using environment variables
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(host=os.getenv("PINECONE_HOST"))

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

def run():
    print(" Mapping Database Signals to Cloud Pinecone Vectors...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT s.id, s.title, m.location_name, s.category, s.is_relevant, s.is_regional, s.location_id 
        FROM safety_signals s
        INNER JOIN monitoring_targets m ON s.location_id = m.id
        WHERE s.category != 'Unclassified'
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print(" No records to sync.")
        cursor.close()
        conn.close()
        return
        

    vectors_to_upsert = []
    print(f" Encoding {len(rows)} signals...")
    
    for row in rows:
        row_id, title, loc_name, cat, rel, reg, loc_id = row
        
        # --- THE GATEKEEPER ---
        # 1. Skip records labeled 'Irrelevant'
        if str(cat).strip() == 'Irrelevant':
            continue
            
        # 2. Skip or sanitize records with no title
        if not title or title.strip() == "":
            print(f"Skipping record {row_id} due to missing title.")
            continue
        # --- END OF GATEKEEPER ---
        
        embedding = embedding_model.encode(title).tolist()
        
        vectors_to_upsert.append({
            "id": f"signal_{row_id}",
            "values": embedding,
            "metadata": {
                "title": str(title),  # <--- ADD THIS LINE
                "location_id": int(loc_id),
                "location_name": str(loc_name),
                "category": str(cat),
                "is_relevant": int(rel or 1),
                "is_regional": int(reg or 0)
            }
        })
    
    # Upsert to Pinecone
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert)
        print(f" Synced {len(vectors_to_upsert)} clean vectors.")
    else:
        print(" No clean records to upsert.")
    
    
    cursor.close()
    conn.close()
    print(" Pinecone Semantic Vector Storage Synced.")

if __name__ == "__main__":
    run()