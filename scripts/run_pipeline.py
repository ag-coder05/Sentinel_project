import sys
import os


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion import vacuum_service
from processing import gemini_processor, predictive_model
from processing.vector_indexing import indexer

def main():
    print("Starting Pipeline")
    
    vacuum_service.run() 
    gemini_processor.run()
    predictive_model.run()
    indexer.run()
    print("Pipeline Completed.")

if __name__ == "__main__":
    main()