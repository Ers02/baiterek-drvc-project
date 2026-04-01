import faiss
import numpy as np
import json
import re
import os
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import text
from ...models import models
from ...core.logger import logger
from ...core.config import settings

class Matcher:
    def __init__(self, db: Session):
        self.db = db

    def match_by_agsk(self, items: list):
        """
        Использует ТОЛЬКО каскадную логику без нечеткого поиска.
        """
        from ..agsk_enstru_matcher import AgskEnstruMatcher
        matcher = AgskEnstruMatcher(self.db)

        for item in items:
            if not item.get('agsk'): continue

            match = matcher.get_match_for_agsk(item['agsk'])
            if match:
                item['found_enstru'] = match['enstru_code']
                item['found_name'] = match['enstru_name']
                item['similarity'] = match['score']
                item['reason'] = match['reason']

    def fuzzy_match_names(self, items: list, update_callback=None):
        """
        Метод оставлен для совместимости, но теперь он ничего не делает по вашему требованию.
        """
        pass

    def load_suppliers(self, items: list):
        found_codes = {i['found_enstru'] for i in items if i.get('found_enstru')}
        if not found_codes: return
        suppliers_map = {}
        for code in found_codes:
            recs = self.db.query(models.Reestr_KTP).filter(models.Reestr_KTP.enstru_codes.op('?')(code)).all()
            suppliers_map[code] = [f"{s.company_name} (БИН: {s.bin_iin})" for s in recs]
        for item in items:
            if item.get('found_enstru'):
                item['suppliers'] = suppliers_map.get(item['found_enstru'], [])
