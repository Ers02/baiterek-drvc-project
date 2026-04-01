import sys
import os
import faiss
import numpy as np
import json
from sentence_transformers import SentenceTransformer

# Добавляем путь к корневой папке 'backend', чтобы импорты работали
# Это делает скрипт запускаемым из любой директории
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.database import SessionLocal
from src.models import models

# Модель для эмбеддингов (многоязычная, хорошо подходит для русского/казахского)
MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

def generate_embeddings():
    print("Загрузка модели эмбеддингов...")
    model = SentenceTransformer(MODEL_NAME)
    
    db = SessionLocal()
    try:
        print("Загрузка данных из Reestr_KTP...")
        # Загружаем уникальные названия и коды
        products = db.query(models.Reestr_KTP.product_name, models.Reestr_KTP.enstru_code).distinct().all()
        
        if not products:
            print("Нет данных для индексации.")
            return

        # Фильтруем пустые названия
        product_data = [(p.product_name, p.enstru_code) for p in products if p.product_name and p.enstru_code]
        
        product_names = [p[0] for p in product_data]
        
        print(f"Найдено {len(product_names)} уникальных названий. Генерация эмбеддингов...")
        
        # Генерируем эмбеддинги (векторы)
        embeddings = model.encode(product_names, convert_to_tensor=True, show_progress_bar=True)
        embeddings = embeddings.cpu().numpy().astype('float32')
        
        # Нормализуем векторы для косинусного сходства
        faiss.normalize_L2(embeddings)
        
        # Создаем индекс FAISS
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension) # IP (Inner Product) эквивалентно косинусному сходству для нормализованных векторов
        index.add(embeddings)
        
        print(f"Индекс создан. Размерность: {dimension}, количество векторов: {index.ntotal}")
        
        # Сохраняем индекс
        index_path = "faiss_index.bin"
        faiss.write_index(index, index_path)
        print(f"Индекс сохранен в {index_path}")
        
        # Создаем маппинг: индекс в FAISS -> (название, код ЕНС ТРУ)
        index_to_data = {i: {"name": name, "code": code} for i, (name, code) in enumerate(product_data)}
        
        mapping_path = "index_to_data.json"
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(index_to_data, f, ensure_ascii=False, indent=4)
        print(f"Маппинг сохранен в {mapping_path}")

    finally:
        db.close()

if __name__ == "__main__":
    generate_embeddings()
