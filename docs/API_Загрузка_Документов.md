# API для загрузки документов в систему ДРВЦ

> **Версия:** 1.0  
> **Базовый URL:** `https://[адрес_системы]/api/external`

---

## Аутентификация

Все запросы требуют передачи API-ключа в заголовке:

```
X-API-Key: ВАШ_API_КЛЮЧ
```

API-ключ выдаётся администратором ДРВЦ. Без корректного ключа сервер вернёт ошибку `401 Unauthorized`.

---

## Проверка доступности API

Перед началом работы убедитесь, что ключ действителен и API доступен:

```
GET /api/external/health
Headers:
  X-API-Key: ВАШ_API_КЛЮЧ
```

**Успешный ответ (200):**
```json
{
  "status": "ok",
  "organization": "Название вашей организации",
  "message": "API-ключ действителен"
}
```

---

## Загрузка документа

```
POST /api/external/upload
Headers:
  X-API-Key: ВАШ_API_КЛЮЧ
  Content-Type: multipart/form-data
```

### Параметры запроса

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|---------|
| `file` | файл | ✅ | Файл документа (см. форматы ниже) |
| `doc_type` | строка | ✅ | Тип документа: `PSD` или `SMETA` |
| `bank_name` | строка | ✅ | Наименование объекта / проекта |
| `received_at` | дата/время | ✅ | Дата отправки в формате ISO 8601 |
| `notes` | строка | ❌ | Дополнительные примечания |
| `sender_first_name` | строка | ✅ | Имя отправителя |
| `sender_last_name` | строка | ✅ | Фамилия отправителя |
| `sender_patronymic` | строка | ✅ | Отчество отправителя |
| `sender_email` | строка | ✅ | Email отправителя |
| `sender_phone` | строка | ✅ | Телефон отправителя |
| `external_id` | строка | ✅ **Рекомендуется** | **Номер документа в вашей АИС. Критичен для группировки ПСД+сметы** |
| `callback_url` | строка | ✅ | URL для получения результата анализа |

---

## ⚠️ ВАЖНО: Группировка документов по проекту

Если вы отправляете **отдельно ПСД и смету** для одного проекта, укажите **одинаковые** `external_id` и `bank_name`:

```python
# Загрузка ПСД
requests.post(API_URL, data={
    "doc_type": "PSD",
    "bank_name": "Строительство школы №15",
    "external_id": "PRJ-2025-001",  # ← ключ группировки
    ...
})

# Загрузка сметы (тот же проект!)
requests.post(API_URL, data={
    "doc_type": "SMETA",
    "bank_name": "Строительство школы №15",  # ← тот же банк
    "external_id": "PRJ-2025-001",  # ← тот же ID
    ...
})
```

**Преимущества:**
- 📁 Документы отображаются как связанная группа
- 👤 Назначение аналитика на один документ = назначение на всю группу
- ⏱️ Единый дедлайн для всего проекта

---

## Типы документов и форматы файлов

### Тип `PSD` — Проектно-сметная документация

Это файлы из сметных программ (KENML-формат).

**Допустимые расширения:**
- `.kenml` — один файл ПСД
- `.zip` — архив, содержащий один или несколько `.kenml` файлов

```
doc_type = "PSD"
file = файл с расширением .kenml или .zip
```

### Тип `SMETA` — Заполненный шаблон сметы

Это Excel-файл по шаблону ДРВЦ (как его скачать — см. отдельную инструкцию).

**Допустимые расширения:**
- `.xlsx`

```
doc_type = "SMETA"
file = файл с расширением .xlsx
```

> ⚠️ **Важно:** Передача файла неверного типа (например, `.kenml` с `doc_type=SMETA`) приведёт к ошибке при обработке. Соблюдайте соответствие.

---

## Примеры запросов

### Python

```python
import requests
from datetime import datetime

API_URL = "https://[адрес_системы]/api/external/upload"
API_KEY = "ВАШ_API_КЛЮЧ"

# Загрузка ПСД (KENML/ZIP)
with open("smeta_shkola.zip", "rb") as f:
    response = requests.post(
        API_URL,
        headers={"X-API-Key": API_KEY},
        data={
            "doc_type": "PSD",
            "bank_name": "Строительство школы на 1200 мест, г. Алматы",
            "received_at": datetime.now().isoformat(),
            "notes": "Основная смета, 1-й этап",
            "sender_last_name": "Иванов",
            "sender_first_name": "Иван",
            "sender_email": "ivanov@example.kz",
            "sender_phone": "+7 701 123 45 67",
            "external_id": "DOC-2025-001",
        },
        files={"file": f},
    )

print(response.status_code, response.json())
```

```python
# Загрузка сметы (Excel-шаблон ДРВЦ)
with open("filled_smeta.xlsx", "rb") as f:
    response = requests.post(
        API_URL,
        headers={"X-API-Key": API_KEY},
        data={
            "doc_type": "SMETA",
            "bank_name": "Реконструкция дороги, ВКО",
            "received_at": datetime.now().isoformat(),
            "sender_last_name": "Петрова",
            "sender_first_name": "Анна",
            "sender_email": "petrova@example.kz",
        },
        files={"file": f},
    )
```

### JavaScript (Node.js)

```javascript
const fs = require('fs');
const FormData = require('form-data');
const axios = require('axios');

const form = new FormData();
form.append('file', fs.createReadStream('smeta_shkola.zip'));
form.append('doc_type', 'PSD');
form.append('bank_name', 'Строительство школы на 1200 мест');
form.append('received_at', new Date().toISOString());
form.append('sender_last_name', 'Иванов');
form.append('sender_email', 'ivanov@example.kz');
form.append('external_id', 'DOC-2025-001');

const response = await axios.post(
  'https://[адрес_системы]/api/external/upload',
  form,
  {
    headers: {
      ...form.getHeaders(),
      'X-API-Key': 'ВАШ_API_КЛЮЧ',
    },
  }
);

console.log(response.data);
```

### cURL

```bash
curl -X POST "https://[адрес_системы]/api/external/upload" \
  -H "X-API-Key: ВАШ_API_КЛЮЧ" \
  -F "file=@smeta_shkola.zip" \
  -F "doc_type=PSD" \
  -F "bank_name=Строительство школы на 1200 мест" \
  -F "received_at=2025-06-01T10:00:00" \
  -F "sender_last_name=Иванов" \
  -F "sender_email=ivanov@example.kz"
```

---

## Успешный ответ (200)

```json
{
  "id": 42,
  "doc_type": "PSD",
  "bank_name": "Строительство школы на 1200 мест, г. Алматы",
  "received_at": "2025-06-01T10:00:00",
  "status": "NEW",
  "file_path": "/uploads/...",
  "notes": "Основная смета, 1-й этап",
  "sender_last_name": "Иванов",
  "sender_first_name": "Иван",
  "sender_email": "ivanov@example.kz",
  "sender_phone": "+7 701 123 45 67",
  "external_id": "DOC-2025-001",
  "is_test": false
}
```

Поле `id` — это идентификатор документа в системе ДРВЦ. Сохраните его для отслеживания статуса.

---

## Коды ошибок

| Код | Причина | Что делать |
|-----|---------|-----------|
| `400` | Неверный формат файла (не `.kenml`, `.zip` или `.xlsx`) | Проверьте расширение файла |
| `400` | Не переданы обязательные поля | Проверьте наличие `file`, `doc_type`, `bank_name`, `received_at` |
| `401` | Отсутствует или неверный API-ключ | Уточните ключ у администратора ДРВЦ |
| `401` | Срок действия API-ключа истёк | Запросите новый ключ у администратора |
| `500` | Внутренняя ошибка сервера | Сообщите в ДРВЦ с текстом ошибки из ответа |

---

## Формат даты `received_at`

Поле `received_at` должно быть в формате **ISO 8601**:

```
2025-06-01T10:30:00        # без часового пояса
2025-06-01T10:30:00+05:00  # с часовым поясом (+5 UTC, Астана)
2025-06-01T05:30:00Z       # UTC
```

---

## Использование `callback_url`

Если вы хотите получать автоматическое уведомление о завершении анализа, передайте `callback_url`. После обработки документа система ДРВЦ отправит POST-запрос на ваш URL со следующими данными:

```
POST {callback_url}
Content-Type: multipart/form-data

document_id: 42
status: completed
file: [Excel-файл с результатами анализа]
```

Ваш сервер должен ответить статусом `200` для подтверждения получения.

---

## Жизненный цикл документа

| Статус | Описание |
|--------|---------|
| `NEW` | Загружен, ожидает назначения |
| `PARSED` | Файл распарсен, позиции извлечены |
| `ASSIGNED_TO_ANALYST` | Назначен аналитику |
| `FOR_APPROVAL` | На утверждении у директора |
| `APPROVED` | Утверждён, формируется ответ |
| `COMPLETED` | Готов к отправке |
| `SENT` | Ответ отправлен вашей организации |
| `ERROR` | Ошибка при обработке |

---

## Контакты

По вопросам подключения и получения API-ключа обращайтесь в ДРВЦ.
