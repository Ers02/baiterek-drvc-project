import os
import sys
import numpy as np
import pandas as pd
import faiss
import json
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.models import models
from src.core.config import settings
from src.core.logger import logger

def create_ktp_index(engine):
    """Creates a FAISS index for the reestr_ktp table."""
    logger.info("Starting KTP index creation...")
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT product_name, enstru_codes 
                FROM reestr_ktp 
                WHERE product_name IS NOT NULL AND product_name != ''
                  AND enstru_codes IS NOT NULL AND jsonb_array_length(enstru_codes) > 0
            """)
            result = connection.execute(query).fetchall()
            df = pd.DataFrame(result, columns=['product_name', 'enstru_codes'])
        
        df.drop_duplicates(subset=['product_name'], inplace=True)
        df['product_name'] = df['product_name'].astype(str)

        if df.empty:
            logger.warning("No KTP data to index. Skipping.")
            return

        logger.info(f"Loaded {len(df)} unique records from Reestr_KTP for indexing.")
        
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        embeddings = model.encode(df['product_name'].tolist(), show_progress_bar=True, convert_to_numpy=True)
        faiss.normalize_L2(embeddings)
        
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
        
        index_path = os.path.join(settings.UPLOAD_DIR, "faiss_index_ktp.bin")
        mapping_path = os.path.join(settings.UPLOAD_DIR, "index_to_data_ktp.json")
        
        faiss.write_index(index, index_path)
        index_to_data_map = df[['product_name', 'enstru_codes']].to_dict(orient='records')
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(index_to_data_map, f, ensure_ascii=False, indent=4)
            
        logger.info("KTP index created successfully.")
        
    except Exception as e:
        logger.error(f"Failed to create KTP index: {e}", exc_info=True)


def create_enstru_index(engine):
    """Creates a FAISS index for the enstru table."""
    logger.info("Starting ENSTRU index creation...")
    try:
        with engine.connect() as connection:
            query = text("""
                SELECT name_rus, code 
                FROM enstru 
                WHERE name_rus IS NOT NULL AND name_rus != '' AND code IS NOT NULL
            """)
            result = connection.execute(query).fetchall()
            df = pd.DataFrame(result, columns=['name_rus', 'code'])

        df.drop_duplicates(subset=['name_rus'], inplace=True)
        
        if df.empty:
            logger.warning("No ENSTRU data to index. Skipping.")
            return
            
        logger.info(f"Loaded {len(df)} unique records from ENSTRU for indexing.")

        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        embeddings = model.encode(df['name_rus'].tolist(), show_progress_bar=True, convert_to_numpy=True)
        faiss.normalize_L2(embeddings)

        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        index_path = os.path.join(settings.UPLOAD_DIR, "faiss_index_enstru.bin")
        mapping_path = os.path.join(settings.UPLOAD_DIR, "index_to_data_enstru.json")

        faiss.write_index(index, index_path)
        index_to_data_map = df[['name_rus', 'code']].to_dict(orient='records')
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(index_to_data_map, f, ensure_ascii=False, indent=4)
            
        logger.info("ENSTRU index created successfully.")

    except Exception as e:
        logger.error(f"Failed to create ENSTRU index: {e}", exc_info=True)


def main():
    """Main function to create all search indexes."""
    logger.info("Starting all search index creation processes...")
    try:
        engine = create_engine(settings.DATABASE_URL, echo=False)
        logger.info("Database connection successful.")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return
        
    create_ktp_index(engine)
    create_enstru_index(engine)
    
    logger.info("All search index creation processes finished.")

if __name__ == "__main__":
    main()
