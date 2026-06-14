# Руководство по интеграции с API ДРВЦ

> **Версия:** 2.0  
> **Дата:** июнь 2025  
> **Базовый URL:** `https://api.drvc.kz/api`

Данное руководство предназначено для разработчиков **дочерних организаций (ДО) АО «Байтерек»**, которые интегрируют свои АИС с системой Дирекции реализации венчурных и целевых программ (ДРВЦ).

---

## Общая схема взаимодействия

```
Ваша АИС                         Система ДРВЦ
    │                                  │
    │  POST /external/upload            │
    │  (ПСД или смета + метаданные)    │
    │ ────────────────────────────────>│
    │                                  │  Автоматический парсинг
    │  ← 200 OK {id: 42, status: NEW}  │  → Назначение аналитика
    │                                  │  → Анализ позиций
    │                                  │  → Утверждение директором
    │                                  │
    │  POST {ваш callback_url}          │
    │  (результат анализа, Excel-файл) │
    │ <────────────────────────────────│
    │                                  │
```

Вы загружаете документ → ДРВЦ обрабатывает → возвращает результат на ваш callback-адрес.

---

## Аутентификация

Каждой дочерней организации выдаётся уникальный **API-ключ**. Он передаётся в заголовке каждого запроса:

```http
X-API-Key: ваш_ключ_здесь
```

**Как получить ключ:** обратитесь к администратору системы ДРВЦ, укажите наименование организации и контактное лицо технической поддержки.

### Проверка ключа

```http
GET /api/external/health
X-API-Key: ваш_ключ_здесь
```

**Ответ (200):**
```json
{
  "status": "ok",
  "organization": "Наименование вашей организации",
  "message": "API-ключ действителен"
}
```

---

## Загрузка документа

```http
POST /api/external/upload
X-API-Key: ваш_ключ_здесь
Content-Type: multipart/form-data
```

### Параметры

| Параметр | Тип | Обяз. | Описание |
|----------|-----|:-----:|----------|
| `file` | файл | ✅ | Файл документа (форматы — ниже) |
| `doc_type` | строка | ✅ | `PSD` — проектно-сметная документация (KENML/ZIP)<br>`SMETA` — смета по шаблону ДРВЦ (Excel) |
| `bank_name` | строка | ✅ | Наименование объекта / проекта |
| `received_at` | ISO 8601 | ✅ | Дата отправки: `2025-06-01T10:30:00` |
| `external_id` | строка | ✅ | **Номер документа в вашей АИС.** Используется для группировки ПСД со сметой и для сверки. Пример: `PRJ-2025-001` |
| `callback_url` | строка | ✅ | URL вашего сервера для получения результата анализа |
| `sender_last_name` | строка | ✅ | Фамилия ответственного |
| `sender_first_name` | строка | ✅ | Имя ответственного |
| `sender_patronymic` | строка | ❌ | Отчество |
| `sender_email` | строка | ✅ | Email ответственного |
| `sender_phone` | строка | ❌ | Телефон |
| `notes` | строка | ❌ | Примечания |

### ⚠️ Поле `external_id` — обязательно

`external_id` — это номер документа в **вашей** системе. Он нужен для:

1. **Группировки** — если вы загружаете ПСД и смету одного проекта отдельными запросами, укажите одинаковый `external_id` в обоих. Тогда они будут обработаны как одна группа.
2. **Сверки** — по этому полю вы сможете найти документ в системе ДРВЦ и сопоставить с вашей АИС.
3. **Уведомлений** — в callback-ответе `external_id` возвращается обратно, чтобы вы знали, к какому документу относится результат.

Формат — любая строка, уникальная в рамках вашей организации.

---

## Форматы файлов

### `doc_type = "PSD"` — проектно-сметная документация

| Расширение | Описание |
|------------|----------|
| `.kenml` | Один файл ПСД |
| `.zip` | Архив с одним или несколькими `.kenml` файлами |

- Максимальный размер: **50 МБ**
- Файлы `.kenml` должны соответствовать спецификации KENML

### `doc_type = "SMETA"` — смета по шаблону ДРВЦ

| Расширение | Описание |
|------------|----------|
| `.xlsx` | Excel-файл по шаблону ДРВЦ |

Шаблон можно скачать без API-ключа:
```
GET https://api.drvc.kz/api/plans/template/download
```

> ⚠️ Несоответствие `doc_type` и формата файла приведёт к ошибке обработки.

---

## Группировка ПСД и сметы

Если для одного проекта загружаются и ПСД, и смета — укажите в обоих запросах **одинаковые** `external_id` и `bank_name`:

```python
# Загрузка ПСД
requests.post(API_URL, data={
    "doc_type": "PSD",
    "bank_name": "Школа на 1200 мест, г. Алматы",
    "external_id": "PRJ-2025-001",   # ← ключ группировки
    "callback_url": "https://your-system.kz/drvc/callback",
    ...
}, files={"file": psd_file})

# Загрузка сметы (тот же проект)
requests.post(API_URL, data={
    "doc_type": "SMETA",
    "bank_name": "Школа на 1200 мест, г. Алматы",   # ← то же название
    "external_id": "PRJ-2025-001",   # ← тот же ID
    "callback_url": "https://your-system.kz/drvc/callback",
    ...
}, files={"file": smeta_file})
```

**Результат:**
- Документы отображаются как одна группа в интерфейсе ДРВЦ
- Аналитик назначается сразу на оба документа
- Общий дедлайн для всего проекта

---

## Примеры запросов

### cURL

```bash
curl -X POST "https://api.drvc.kz/api/external/upload" \
  -H "X-API-Key: ваш_ключ_здесь" \
  -F "file=@projekt_shkola.zip" \
  -F "doc_type=PSD" \
  -F "bank_name=Школа на 1200 мест, г. Алматы" \
  -F "received_at=2025-06-01T10:30:00" \
  -F "external_id=PRJ-2025-001" \
  -F "callback_url=https://your-system.kz/drvc/callback" \
  -F "sender_last_name=Иванов" \
  -F "sender_first_name=Пётр" \
  -F "sender_email=ivanov@example.kz"
```

### Python

```python
import requests
from datetime import datetime

API_URL = "https://api.drvc.kz/api/external/upload"
API_KEY = "ваш_ключ_здесь"

with open("projekt_shkola.zip", "rb") as f:
    response = requests.post(
        API_URL,
        headers={"X-API-Key": API_KEY},
        data={
            "doc_type": "PSD",
            "bank_name": "Школа на 1200 мест, г. Алматы",
            "received_at": datetime.now().isoformat(),
            "external_id": "PRJ-2025-001",
            "callback_url": "https://your-system.kz/drvc/callback",
            "sender_last_name": "Иванов",
            "sender_first_name": "Пётр",
            "sender_email": "ivanov@example.kz",
            "sender_phone": "+7 701 123 45 67",
        },
        files={"file": f},
    )

print(response.status_code, response.json())
```

### JavaScript (Node.js)

```javascript
const fs = require('fs');
const FormData = require('form-data');
const axios = require('axios');

const form = new FormData();
form.append('file', fs.createReadStream('projekt_shkola.zip'));
form.append('doc_type', 'PSD');
form.append('bank_name', 'Школа на 1200 мест, г. Алматы');
form.append('received_at', new Date().toISOString());
form.append('external_id', 'PRJ-2025-001');
form.append('callback_url', 'https://your-system.kz/drvc/callback');
form.append('sender_last_name', 'Иванов');
form.append('sender_email', 'ivanov@example.kz');

const response = await axios.post(
  'https://api.drvc.kz/api/external/upload',
  form,
  { headers: { ...form.getHeaders(), 'X-API-Key': 'ваш_ключ_здесь' } }
);

console.log(response.data);
```

### C# (HttpClient)

```csharp
using var client = new HttpClient();
client.DefaultRequestHeaders.Add("X-API-Key", "ваш_ключ_здесь");

using var form = new MultipartFormDataContent();
form.Add(new StringContent("PSD"), "doc_type");
form.Add(new StringContent("Школа на 1200 мест, г. Алматы"), "bank_name");
form.Add(new StringContent("2025-06-01T10:30:00"), "received_at");
form.Add(new StringContent("PRJ-2025-001"), "external_id");
form.Add(new StringContent("https://your-system.kz/drvc/callback"), "callback_url");
form.Add(new StringContent("Иванов"), "sender_last_name");
form.Add(new StringContent("Пётр"), "sender_first_name");
form.Add(new StringContent("ivanov@example.kz"), "sender_email");

var fileContent = new StreamContent(File.OpenRead("projekt_shkola.zip"));
form.Add(fileContent, "file", "projekt_shkola.zip");

var response = await client.PostAsync("https://api.drvc.kz/api/external/upload", form);
Console.WriteLine(await response.Content.ReadAsStringAsync());
```

### 1С (8.x)

```bsl
&НаСервере
Процедура ОтправитьПСДНаСервере()

    Адрес    = "https://api.drvc.kz/api/external/upload";
    АПИКлюч  = "ваш_ключ_здесь";
    Разделитель = "----Boundary" + Строка(Новый УникальныйИдентификатор);

    Заголовки = Новый Соответствие;
    Заголовки.Вставить("X-API-Key", АПИКлюч);
    Заголовки.Вставить("Content-Type", "multipart/form-data; boundary=" + Разделитель);

    ТелоЗапроса = Новый ПотокВПамяти();
    Запись = Новый ЗаписьДанных(ТелоЗапроса);

    // Файл
    Запись.ЗаписатьСтроку("--" + Разделитель);
    Запись.ЗаписатьСтроку("Content-Disposition: form-data; name=""file""; filename=""projekt.zip""");
    Запись.ЗаписатьСтроку("Content-Type: application/octet-stream");
    Запись.ЗаписатьСтроку("");
    Запись.Записать(Новый ДвоичныеДанные("C:\temp\projekt.zip"));
    Запись.ЗаписатьСтроку("");

    // Поля
    Поля = Новый Соответствие;
    Поля.Вставить("doc_type",      "PSD");
    Поля.Вставить("bank_name",     "Школа на 1200 мест, г. Алматы");
    Поля.Вставить("received_at",   Формат(ТекущаяДата(), "ДФ=yyyy-MM-ddTHH:mm:ss"));
    Поля.Вставить("external_id",   "PRJ-2025-001");
    Поля.Вставить("callback_url",  "https://your-system.kz/drvc/callback");
    Поля.Вставить("sender_last_name",  "Иванов");
    Поля.Вставить("sender_first_name", "Пётр");
    Поля.Вставить("sender_email",      "ivanov@example.kz");

    Для Каждого Поле Из Поля Цикл
        Запись.ЗаписатьСтроку("--" + Разделитель);
        Запись.ЗаписатьСтроку("Content-Disposition: form-data; name=""" + Поле.Ключ + """");
        Запись.ЗаписатьСтроку("");
        Запись.ЗаписатьСтроку(Поле.Значение);
    КонецЦикла;

    Запись.ЗаписатьСтроку("--" + Разделитель + "--");
    Запись.Закрыть();

    Соединение = Новый HTTPСоединение(
        "api.drvc.kz", 443, , , , ,
        Новый ЗащищенноеСоединениеOpenSSL()
    );
    Запрос = Новый HTTPЗапрос("/api/external/upload", Заголовки);
    Запрос.УстановитьТелоИзДвоичныхДанных(
        ТелоЗапроса.ЗакрытьИПолучитьДвоичныеДанные()
    );

    Ответ = Соединение.ОтправитьДляОбработки(Запрос);
    Сообщить("Статус: " + Ответ.КодСостояния);

КонецПроцедуры
```

---

## Ответ API

### Успешный ответ (200)

```json
{
  "id": 42,
  "doc_type": "PSD",
  "bank_name": "Школа на 1200 мест, г. Алматы",
  "received_at": "2025-06-01T10:30:00",
  "status": "NEW",
  "external_id": "PRJ-2025-001",
  "notes": null,
  "is_test": false
}
```

Поле `id` — идентификатор документа в системе ДРВЦ. Сохраните его для возможной сверки.

### Коды ошибок

| Код | Причина | Что делать |
|-----|---------|-----------|
| 400 | Неверный формат файла или отсутствуют обязательные поля | Проверьте `doc_type`, расширение файла и наличие всех обязательных полей |
| 401 | Отсутствует или неверный API-ключ | Проверьте заголовок `X-API-Key`, при необходимости запросите новый ключ |
| 422 | Ошибка валидации данных | Проверьте формат `received_at` и типы данных |
| 413 | Файл слишком большой | Максимальный размер — 50 МБ; разбейте данные на несколько файлов |
| 500 | Внутренняя ошибка сервера | Сообщите в ДРВЦ с `id` запроса и текстом ошибки |

---

## Жизненный цикл документа

| Статус | Описание |
|--------|----------|
| `NEW` | Загружен, ожидает назначения аналитика |
| `PARSED` | Файл распарсен, позиции извлечены |
| `ASSIGNED_TO_ANALYST` | Назначен аналитику |
| `FOR_APPROVAL` | На утверждении у директора ДРВЦ |
| `APPROVED` | Утверждён, формируется ответный файл |
| `COMPLETED` | Готов к отправке |
| `SENT` | Результат отправлен на ваш `callback_url` |
| `ERROR` | Ошибка при обработке; обратитесь в поддержку |

---

## Получение результата (Callback)

После завершения анализа система ДРВЦ отправит **POST-запрос** на ваш `callback_url`:

```http
POST {ваш_callback_url}
Content-Type: multipart/form-data

document_id:  42
external_id:  PRJ-2025-001
status:       completed
file:         [Excel-файл с результатами анализа]
```

Ваш сервер должен ответить статусом **200 OK**. Если ответа нет — система повторит попытку через 5 минут (до 3 раз).

> Подробные требования к вашему callback-эндпоинту см. в документе **«Требования к API дочерних организаций»**.

---

## Часто задаваемые вопросы

**В: Можно ли загрузить несколько KENML в одном запросе?**  
О: Да — упакуйте их в один ZIP-архив и передайте с `doc_type=PSD`.

**В: Что если `callback_url` недоступен?**  
О: Система повторит попытку 3 раза с интервалом 5 минут. Если все попытки неудачны — документ останется в статусе `COMPLETED`. Свяжитесь с администратором ДРВЦ для повторной отправки.

**В: Можно ли отправить тестовый документ?**  
О: Да — добавьте параметр `is_test=true`. Тестовые документы обрабатываются, но не включаются в общую отчётность.

**В: Что делать при ошибке 500?**  
О: Сохраните тело ответа (там будет описание ошибки) и обратитесь в поддержку ДРВЦ.

---

## Контакты

| | |
|---|---|
| Email | support@drvc.kz |
| Телефон | +7 (7172) 55-05-20 |
| Ответственный за интеграцию | Уточнить у куратора проекта |
