import io
import zipfile
import xml.etree.ElementTree as ET
from fastapi import UploadFile, HTTPException

def get_float(val):
    try:
        if val is None: return 0.0
        clean_val = str(val).replace(',', '.').replace('\xa0', '').replace(' ', '')
        return float(clean_val)
    except ValueError:
        return 0.0

def clean_str(val):
    if not val: return ""
    return str(val).strip()

def clean_snb(snb, local_code):
    s = clean_str(snb)
    if not s:
        l = clean_str(local_code)
        return l if l else "БЕЗ_КОДА"
    return s

class KenmlParser:
    def __init__(self, file_content: bytes, filename: str):
        self.filename = filename
        self.tree = ET.fromstring(file_content)
        self.root = self.tree
        self.version = self.root.get("ВерсияФормата") or self.root.get("Version") or "01.00"
        
    def parse(self):
        if self.version.startswith("02"):
            return self._parse_v2()
        else:
            return self._parse_v1()

    def _make_row(self, cat, name, code, unit, price, vol, total, logic):
        return {
            "Категория": cat, 
            "Наименование": clean_str(name), 
            "КодСНБ": code, 
            "Ед. изм.": clean_str(unit), 
            "Цена за ед.": price, 
            "Объем": vol, 
            "Сумма": total,
            "Логика": logic,
            "Источник": self.filename
        }

    def _parse_v1(self):
        data = []
        control_sum = 0.0
        for pos in self.root.findall(".//ПОЗИЦИЯ"):
            p_type = pos.get("Тип")
            p_code = clean_snb(pos.get("КодСНБ"), pos.get("КодЛокальный"))
            p_name = pos.get("Наименование", "")
            p_unit = pos.get("Измеритель", "")
            p_vol = get_float(pos.get("Объем"))
            
            cost_elem = pos.find("СТОИМОСТЬ/ВСЕГО")
            p_total_orig = get_float(cost_elem.get("ВСЕГО")) if cost_elem is not None else 0.0
            control_sum += p_total_orig

            if p_type == "0": # Работа
                mats_deduction = 0.0
                extracted_mats = []
                for res in pos.findall("РЕСУРС"):
                    if res.get("Тип") == "2":
                        r_vol = get_float(res.get("Объем"))
                        r_price = get_float(res.get("Цена"))
                        r_total = r_vol * r_price
                        if r_total > 0.0001:
                            mats_deduction += r_total
                            extracted_mats.append(self._make_row("Товары", res.get("Наименование"), clean_snb(res.get("КодСНБ"), res.get("КодЛокальный")), res.get("Измеритель"), r_price, r_vol, r_total, "Материал из работы"))
                
                work_net = p_total_orig - mats_deduction
                work_price = work_net / p_vol if p_vol else 0
                data.append(self._make_row("Работы", p_name, p_code, p_unit, work_price, p_vol, work_net, "СМР (Остаток)"))
                data.extend(extracted_mats)
            else:
                cat = "Товары" if p_type in ["1", "2"] else "Услуги"
                price = p_total_orig / p_vol if p_vol else 0
                data.append(self._make_row(cat, p_name, p_code, p_unit, price, p_vol, p_total_orig, "Прямая позиция"))
        return data, control_sum

    def _parse_v2(self):
        data = []
        control_sum = 0.0
        items = self.root.findall(".//Item") or self.root.findall(".//ПОЗИЦИЯ")
        for it in items:
            p_type = it.get("Type") or it.get("Тип")
            p_code = clean_snb(it.get("Code") or it.get("КодСНБ"), it.get("LocalCode") or it.get("КодЛокальный"))
            p_name = it.get("Name") or it.get("Наименование")
            p_unit = it.get("Unit") or it.get("Измеритель")
            p_vol = get_float(it.get("Quantity") or it.get("Объем"))
            
            cost_node = it.find("Cost") or it.find("СТОИМОСТЬ")
            p_total_orig = 0.0
            if cost_node is not None:
                p_total_orig = get_float(cost_node.get("Summary") or cost_node.get("Total") or cost_node.get("Всего"))
            if p_total_orig == 0:
                v_el = it.find(".//ВСЕГО")
                if v_el is not None: p_total_orig = get_float(v_el.get("ВСЕГО"))
            control_sum += p_total_orig

            if p_type == "0" or it.get("WorkType"):
                mats_deduction = 0.0
                extracted_mats = []
                resources = it.findall("Resource") or it.findall("РЕСУРС")
                for res in resources:
                    r_type = res.get("Type") or res.get("Тип")
                    if r_type == "2" or res.get("MaterialType"):
                        rv = get_float(res.get("Quantity") or res.get("Объем"))
                        rp = get_float(res.get("Price") or res.get("Цена"))
                        rt = rv * rp
                        if rt > 0.0001:
                            mats_deduction += rt
                            extracted_mats.append(self._make_row("Товары", res.get("Name") or res.get("Наименование"), res.get("Code") or res.get("КодСНБ"), res.get("Unit") or res.get("Измеритель"), rp, rv, rt, "Материал из работы"))
                
                work_net = p_total_orig - mats_deduction
                work_price = work_net / p_vol if p_vol else 0
                data.append(self._make_row("Работы", p_name, p_code, p_unit, work_price, p_vol, work_net, "СМР (Остаток)"))
                data.extend(extracted_mats)
            else:
                cat = "Товары" if p_type in ["1", "2"] else "Услуги"
                price = p_total_orig / p_vol if p_vol else 0
                data.append(self._make_row(cat, p_name, p_code, p_unit, price, p_vol, p_total_orig, "Прямая позиция"))
        return data, control_sum

def parse_kenml_file(file: UploadFile) -> list[dict]:
    """
    Парсит KENML/ZIP файл и возвращает список словарей с данными.
    """
    all_data = []
    try:
        content = file.file.read()
        
        if file.filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(content), 'r') as z:
                for filename in z.namelist():
                    if filename.endswith('.kenml'):
                        with z.open(filename) as f:
                            parser = KenmlParser(f.read(), filename)
                            data, _ = parser.parse()
                            all_data.extend(data)
        elif file.filename.endswith('.kenml') or file.filename.endswith('.xml'):
             parser = KenmlParser(content, file.filename)
             data, _ = parser.parse()
             all_data.extend(data)
        else:
             raise HTTPException(status_code=400, detail="Поддерживаются только .kenml, .xml или .zip файлы")
             
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка обработки файла: {str(e)}")
        
    return all_data
