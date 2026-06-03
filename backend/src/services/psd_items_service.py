"""Работа с позициями документа ПСД + выборы поставщиков аналитиком.

Используется как миксин в PsdAnalystService.
"""
from collections import defaultdict
from typing import Dict, Optional

from sqlalchemy import case, desc, func, or_
from sqlalchemy.orm import Session

from ..models.models import (
    Agsk, AgskEnstruMatch, Enstru, PsdDocumentItem, PsdItemSupplierSelection,
)


class PsdItemsMixin:
    def get_document_items_with_matches(
            self, db: Session, doc_id: int,
            only_unmatched: bool = False,
            search: Optional[str] = None,
            skip: int = 0, limit: int = 50,
    ):
        query = db.query(PsdDocumentItem).filter(PsdDocumentItem.document_id == doc_id)
        if search:
            q = search.strip()
            query = query.filter(or_(
                PsdDocumentItem.name.ilike(f"%{q}%"),
                PsdDocumentItem.code_sn.ilike(f"%{q}%"),
            ))
        if only_unmatched:
            # «Необработанная» позиция = GOODS с match_type в ('none', 'suggested'),
            # не отмечена «нет в реестре» и не имеет активного выбора поставщика.
            # auto/auto_ktp = АГСК прямо в реестре КТП → уже обработаны, не показываем.
            active_item_subq = db.query(PsdItemSupplierSelection.item_id).filter(
                PsdItemSupplierSelection.status == 'active',
                PsdItemSupplierSelection.is_active == True,
            ).subquery()
            query = query.filter(
                PsdDocumentItem.item_type.in_(['GOODS', None]),
                or_(
                    PsdDocumentItem.not_in_ktp_registry == False,
                    PsdDocumentItem.not_in_ktp_registry == None,
                ),
                ~PsdDocumentItem.id.in_(active_item_subq),
                # auto/auto_ktp — АГСК напрямую в КТП, считаются обработанными
                ~PsdDocumentItem.match_type.in_(['auto', 'auto_ktp']),
            )
        # Сортировка:
        # Вверх: 'none' / 'suggested' — требуют действия аналитика
        # Вниз:  'manual' / 'auto' / 'auto_ktp' / 'manual_ktp' — обработаны
        # Самый низ: OTHER/BALANCE
        query = query.order_by(
            case((PsdDocumentItem.item_type == 'OTHER', 2), else_=0),
            desc(
                PsdDocumentItem.match_type.in_(['none', 'suggested']) &
                (
                    (PsdDocumentItem.not_in_ktp_registry == False) |
                    (PsdDocumentItem.not_in_ktp_registry == None)
                )
            ),
            PsdDocumentItem.match_score.asc(),
            PsdDocumentItem.id.asc()
        )
        total_count = query.count()
        items = query.offset(skip).limit(limit).all()
        agsk_codes = [it.code_sn for it in items if it.code_sn]
        agsk_map = {}
        if agsk_codes:
            agsk_data = db.query(Agsk).filter(Agsk.code.in_(agsk_codes)).all()
            agsk_map = {a.code: a for a in agsk_data}

        # Загружаем активные выборы поставщиков для каждой позиции
        item_ids = [it.id for it in items]
        selections_by_item: Dict[int, list] = defaultdict(list)
        if item_ids:
            sel_list = db.query(PsdItemSupplierSelection).filter(
                PsdItemSupplierSelection.item_id.in_(item_ids),
                PsdItemSupplierSelection.is_active == True,
            ).order_by(PsdItemSupplierSelection.id.desc()).all()
            for s in sel_list:
                selections_by_item[s.item_id].append(s)

        # Считаем кол-во библиотечных записей АГСК→ЕНСТРУ, ожидающих утверждения менеджером.
        # (Выборы поставщиков не требуют утверждения — они сразу активны.)
        pending_match_count = 0
        agsk_codes_page = [it.code_sn for it in items if it.code_sn]
        if agsk_codes_page:
            pending_match_count = db.query(AgskEnstruMatch).filter(
                AgskEnstruMatch.agsk_code.in_(agsk_codes_page),
                AgskEnstruMatch.is_approved == False,
                AgskEnstruMatch.is_active == True,
            ).count()

        result = []
        for item in items:
            agsk_info = agsk_map.get(item.code_sn)
            item_selections = selections_by_item.get(item.id, [])
            current_manual_matches = []
            for sel in item_selections:
                current_manual_matches.append({
                    "id": sel.id,
                    "enstru_code": sel.enstru_code or "",
                    "status": sel.status,  # 'pending' | 'active' | 'rejected'
                    "ktp_id": sel.ktp_id,
                    "supplier_name": sel.supplier_name,
                    "supplier_bin": sel.supplier_bin,
                    "supplier_product": sel.supplier_product,
                    "dvc_percent": float(sel.dvc_percent) if sel.dvc_percent else None,
                    "matched_at": sel.selected_at.isoformat() if sel.selected_at else None,
                    "approved_at": None,  # не применимо к выборам (утверждение на уровне библиотеки)
                })

            result.append({
                "id": item.id, "item_id": item.id, "document_id": item.document_id,
                "position_number": item.position_number, "name": item.name, "code_sn": item.code_sn,
                "unit": item.unit,
                "volume": float(item.volume) if item.volume else 0,
                "price": float(item.price) if item.price else 0,
                "total_amount": float(item.total_amount) if item.total_amount else 0,
                "enstru_code": item.enstru_code, "enstru_name": item.enstru_name,
                "match_type": item.match_type, "match_score": item.match_score,
                "match_reason": item.match_reason,
                "not_in_ktp_registry": bool(item.not_in_ktp_registry) if item.not_in_ktp_registry is not None else False,
                "can_edit": True,
                "agsk_name_ru": agsk_info.name_ru if agsk_info else None,
                "agsk_full_name": agsk_info.full_name if agsk_info else None,
                "item_type": item.item_type or "GOODS",
                "current_manual_matches": current_manual_matches,
            })
        return {"items": result, "total": total_count, "skip": skip, "limit": limit, "pending_match_count": pending_match_count}

    # ── Выбор поставщика с approval-воркфлоу ────────────────────────────────

    def add_supplier_selection(
        self,
        db: Session,
        item_id: int,
        enstru_code: str,
        analyst_id: int,
        ktp_id: Optional[int] = None,
        product_code: Optional[str] = None,
        supplier_bin: Optional[str] = None,
        supplier_name: Optional[str] = None,
        supplier_product: Optional[str] = None,
        dvc_percent: Optional[float] = None,
    ) -> PsdItemSupplierSelection:
        """Аналитик выбирает поставщика из Реестра КТП для позиции ПСД.

        Логика статуса:
        - Выбор поставщика ВСЕГДА сразу status='active', позиция сразу обработана.
        - Если АГСК→ЕНСТРУ пара новая — создаётся библиотечная запись на рассмотрение менеджером,
          но сам выбор поставщика НЕ блокируется ожиданием.
        - Решение о добавлении в библиотеку принимает менеджер отдельно.
        """
        item = db.query(PsdDocumentItem).filter(PsdDocumentItem.id == item_id).first()
        if not item:
            raise ValueError("Позиция документа не найдена")

        agsk_code = item.code_sn or ""

        # Проверяем дубликат: тот же ktp_id + enstru_code уже активен для позиции
        dup_filter = [
            PsdItemSupplierSelection.item_id == item_id,
            PsdItemSupplierSelection.enstru_code == enstru_code,
            PsdItemSupplierSelection.is_active == True,
        ]
        if ktp_id is not None:
            dup_filter.append(PsdItemSupplierSelection.ktp_id == ktp_id)
        duplicate = db.query(PsdItemSupplierSelection).filter(*dup_filter).first()
        if duplicate:
            raise ValueError("Этот поставщик уже выбран для данной позиции")

        # ── Библиотечная запись АГСК→ЕНСТРУ (для менеджера, не блокирует выбор) ─
        library_match_id: Optional[int] = None

        # Создаём/реактивируем библиотечную запись только для не-авто позиций
        # (для auto/auto_ktp АГСК уже напрямую есть в реестре КТП — библиотека не нужна)
        is_auto = item.match_type in ('auto', 'auto_ktp')
        if not is_auto and agsk_code:
            match = db.query(AgskEnstruMatch).filter(
                AgskEnstruMatch.agsk_code == agsk_code,
                AgskEnstruMatch.enstru_code == enstru_code,
            ).first()

            if match is None:
                # Новая пара — создаём запись на рассмотрение менеджером (не блокирует выбор)
                match = AgskEnstruMatch(
                    agsk_code=agsk_code,
                    enstru_code=enstru_code,
                    created_by=analyst_id,
                    is_approved=False,
                    is_active=True,
                )
                db.add(match)
                db.flush()
            elif not match.is_active:
                # Реактивируем ранее отклонённую запись → снова на рассмотрение менеджером
                match.is_active = True
                match.is_approved = False
                match.created_by = analyst_id
                match.created_at = func.now()
                db.flush()

            library_match_id = match.id

        # ── Создаём запись выбора поставщика (всегда active) ───────────────────
        selection = PsdItemSupplierSelection(
            item_id=item_id,
            agsk_code=agsk_code,
            enstru_code=enstru_code,
            ktp_id=ktp_id,
            product_code=product_code,
            supplier_bin=supplier_bin,
            supplier_name=supplier_name,
            supplier_product=supplier_product,
            dvc_percent=dvc_percent,
            selected_by=analyst_id,
            library_match_id=library_match_id,
            status='active',  # всегда активен — не ждём одобрения менеджером
            is_active=True,
        )
        db.add(selection)

        # ── Обновляем позицию — сразу помечаем как обработанную ────────────────
        enstru_obj = db.query(Enstru).filter(Enstru.code == enstru_code).first()
        item.enstru_code = enstru_code
        item.enstru_name = enstru_obj.name_rus if enstru_obj else None
        item.match_type = "manual"
        item.match_score = 100
        item.match_reason = "Выбор аналитика из реестра КТП"

        db.commit()
        db.refresh(selection)
        return selection

    def remove_supplier_selection(self, db: Session, sel_id: int, analyst_id: int) -> None:
        """Аналитик удаляет свой выбор поставщика.
        Если активных выборов не осталось — откатывает match_type позиции обратно в 'suggested'/'none'."""
        sel = db.query(PsdItemSupplierSelection).filter(PsdItemSupplierSelection.id == sel_id).first()
        if not sel:
            raise ValueError("Выбор поставщика не найден")
        if sel.selected_by != analyst_id:
            raise ValueError("Нет прав для удаления этого выбора")

        item_id = sel.item_id
        sel.is_active = False
        db.flush()

        # Откатываем match_type если больше нет активных выборов
        remaining = db.query(PsdItemSupplierSelection).filter(
            PsdItemSupplierSelection.item_id == item_id,
            PsdItemSupplierSelection.is_active == True,
        ).count()
        if remaining == 0:
            item = db.query(PsdDocumentItem).filter(PsdDocumentItem.id == item_id).first()
            if item:
                item.match_type = 'suggested' if item.enstru_code else 'none'
                item.match_reason = 'Подсказка из библиотеки — поставщик удалён, выберите нового из реестра КТП'

        db.commit()
