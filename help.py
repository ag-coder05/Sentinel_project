# Create a quick delete_all.py script
from pinecone import Pinecone
import os
from dotenv import load_dotenv

load_dotenv()
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(host=os.getenv("PINECONE_HOST"))

# Deletes all vectors in the default namespace
index.delete(delete_all=True)
print("Index cleared!")