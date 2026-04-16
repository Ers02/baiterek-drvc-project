# Инструкция по интеграции с API ДРВЦ

## Общая информация

Данная инструкция предназначена для дочерних организаций, которым необходимо отправлять данные ПСД (Проектно-Сметную Документацию) в систему ДРВЦ для анализа и сопоставления с классификатором АГСК.

**Базовый URL:** `https://api.drvc.kz/api`

## Аутентификация

Все запросы к API требуют аутентификации через API-ключ, который выдаётся каждой дочерней организации.

### Получение API-ключа

1. Обратитесь к администратору системы ДРВЦ
2. Укажите наименование вашей организации
3. Получите уникальный API-ключ для доступа

### Передача API-ключа

API-ключ передаётся в заголовке `X-API-Key`:

```http
X-API-Key: your_api_key_here
```

## Endpoint: Загрузка документа

### URL
```
POST /external/upload
```

### Content-Type
```
multipart/form-data
```

### Заголовки
| Заголовок | Обязательный | Описание |
|-----------|--------------|----------|
| X-API-Key | Да | Ваш API-ключ |

### Параметры формы (Form Data)
| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| file | File | Да | Файл документа (.kenml или .zip) |
| doc_type | String | Да | Тип документа: `PSD` или `SMETA` |
| bank_name | String | Да | Наименование банка/проекта |
| received_at | ISO 8601 DateTime | Да | Дата и время отправки (формат: `2024-01-15T10:30:00`) |
| notes | String | Нет | Дополнительные примечания |

### Данные отправителя (опционально)
| Параметр | Тип | Описание |
|----------|-----|----------|
| sender_first_name | String | Имя отправителя |
| sender_last_name | String | Фамилия отправителя |
| sender_patronymic | String | Отчество отправителя |
| sender_email | String | Email для обратной связи |
| sender_phone | String | Телефон для обратной связи |

### Параметры для callback (опционально)
| Параметр | Тип | Описание |
|----------|-----|----------|
| external_id | String | ID документа в вашей системе |
| callback_url | String | URL для отправки результата анализа |

## Примеры запросов

### cURL

```bash
curl -X POST "https://api.drvc.kz/api/external/upload" \
  -H "X-API-Key: your_api_key_here" \
  -F "file=@/path/to/your/document.kenml" \
  -F "doc_type=PSD" \
  -F "bank_name=Банк Развития - Проект Офис" \
  -F "received_at=2024-01-15T10:30:00" \
  -F "notes=ПСД на строительство адм. здания" \
  -F "sender_last_name=Иванов" \
  -F "sender_first_name=Петр" \
  -F "sender_email=ivanov@example.kz"
```

### Python (requests)

```python
import requests

url = "https://api.drvc.kz/api/external/upload"
headers = {
    "X-API-Key": "your_api_key_here"
}
data = {
    "doc_type": "PSD",
    "bank_name": "Банк Развития - Проект Офис",
    "received_at": "2024-01-15T10:30:00",
    "notes": "ПСД на строительство адм. здания",
    "sender_last_name": "Иванов",
    "sender_first_name": "Петр",
    "sender_email": "ivanov@example.kz"
}

with open("document.kenml", "rb") as f:
    files = {"file": f}
    response = requests.post(url, headers=headers, data=data, files=files)

print(response.json())
```

### JavaScript (fetch)

```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);
formData.append("doc_type", "PSD");
formData.append("bank_name", "Банк Развития - Проект Офис");
formData.append("received_at", "2024-01-15T10:30:00");
formData.append("sender_last_name", "Иванов");
formData.append("sender_first_name", "Петр");
formData.append("sender_email", "ivanov@example.kz");

fetch("https://api.drvc.kz/api/external/upload", {
    method: "POST",
    headers: {
        "X-API-Key": "your_api_key_here"
    },
    body: formData
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error("Error:", error));
```

### C# (HttpClient)

```csharp
using var client = new HttpClient();
using var form = new MultipartFormDataContent();

client.DefaultRequestHeaders.Add("X-API-Key", "your_api_key_here");

form.Add(new StringContent("PSD"), "doc_type");
form.Add(new StringContent("Банк Развития - Проект Офис"), "bank_name");
form.Add(new StringContent("2024-01-15T10:30:00"), "received_at");
form.Add(new StringContent("Иванов"), "sender_last_name");
form.Add(new StringContent("Петр"), "sender_first_name");
form.Add(new StringContent("ivanov@example.kz"), "sender_email");

var fileContent = new StreamContent(File.OpenRead("document.kenml"));
form.Add(fileContent, "file", "document.kenml");

var response = await client.PostAsync("https://api.drvc.kz/api/external/upload", form);
var result = await response.Content.ReadAsStringAsync();
Console.WriteLine(result);
```

### 1C

```bsl
&НаСервере
Процедура ОтправитьПСДНаСервере()
    
    Адрес = "https://api.drvc.kz/api/external/upload";
    
    // Формируем заголовки
    Заголовки = Новый Соответствие;
    Заголовки.Вставить("X-API-Key", "your_api_key_here");
    
    // Формируем тело запроса (multipart/form-data)
    Разделитель = "----WebKitFormBoundary" + Строка(Новый УникальныйИдентификатор);
    
    ТелоЗапроса = Новый ПотокВПамяти();
    ЗаписьДанных = Новый ЗаписьДанных(ТелоЗапроса);
    
    // Добавляем файл
    ЗаписьДанных.ЗаписатьСтроку("--" + Разделитель);
    ЗаписьДанных.ЗаписатьСтроку("Content-Disposition: form-data; name=""file""; filename=""document.kenml""");
    ЗаписьДанных.ЗаписатьСтроку("Content-Type: application/octet-stream");
    ЗаписьДанных.ЗаписатьСтроку("");
    
    ДанныеФайла = Новый ДвоичныеДанные("C:\\temp\\document.kenml");
    ЗаписьДанных.Записать(ДанныеФайла);
    ЗаписьДанных.ЗаписатьСтроку("");
    
    // Добавляем поля формы
    Поля = Новый Соответствие;
    Поля.Вставить("doc_type", "PSD");
    Поля.Вставить("bank_name", "Банк Развития - Проект Офис");
    Поля.Вставить("received_at", Формат(ТекущаяДата(), "ДФ=yyyy-MM-ddTHH:mm:ss"));
    Поля.Вставить("sender_last_name", "Иванов");
    Поля.Вставить("sender_first_name", "Петр");
    Поля.Вставить("sender_email", "ivanov@example.kz");
    
    Для Каждого Поле Из Поля Цикл
        ЗаписьДанных.ЗаписатьСтроку("--" + Разделитель);
        ЗаписьДанных.ЗаписатьСтроку("Content-Disposition: form-data; name=""" + Поле.Ключ + """");
        ЗаписьДанных.ЗаписатьСтроку("");
        ЗаписьДанных.ЗаписатьСтроку(Поле.Значение);
    КонецЦикла;
    
    ЗаписьДанных.ЗаписатьСтроку("--" + Разделитель + "--");
    ЗаписьДанных.Закрыть();
    
    ТелоДвоичныеДанные = ТелоЗапроса.ЗакрытьИПолучитьДвоичныеДанные();
    
    Заголовки.Вставить("Content-Type", "multipart/form-data; boundary=" + Разделитель);
    
    Соединение = Новый HTTPСоединение("api.drvc.kz", 443, , , , , Новый ЗащищенноеСоединениеOpenSSL());
    Запрос = Новый HTTPЗапрос("/api/external/upload", Заголовки);
    Запрос.УстановитьТелоИзДвоичныхДанных(ТелоДвоичныеДанные);
    
    Ответ = Соединение.ОтправитьДляОбработки(Запрос);
    
    Если Ответ.КодСостояния = 200 Тогда
        Сообщить("Файл успешно отправлен");
    Иначе
        Сообщить("Ошибка: " + Ответ.КодСостояния);
    КонецЕсли;
    
КонецПроцедуры
```

## Ответ API

### Успешный ответ (200 OK)

```json
{
  "id": 12345,
  "doc_type": "PSD",
  "bank_name": "Банк Развития - Проект Офис",
  "sender_first_name": "Петр",
  "sender_last_name": "Иванов",
  "sender_email": "ivanov@example.kz",
  "received_at": "2024-01-15T10:30:00",
  "status": "NEW",
  "file_path": "/uploads/uuid_filename.kenml",
  "notes": "ПСД на строительство адм. здания"
}
```

### Ошибки

| Код | Описание | Решение |
|-----|----------|---------|
| 401 | Неверный или отсутствующий API-ключ | Проверьте заголовок X-API-Key |
| 400 | Некорректные данные | Проверьте формат данных и обязательные поля |
| 422 | Ошибка валидации | Проверьте типы данных (например, формат даты) |
| 500 | Внутренняя ошибка сервера | Обратитесь к администратору |

### Пример ошибки (422)

```json
{
  "detail": [
    {
      "loc": ["body", "received_at"],
      "msg": "invalid datetime format",
      "type": "value_error.datetime"
    }
  ]
}
```

## Форматы файлов

### Поддерживаемые форматы
- `.kenml` — файл в формате KENML (Казахстанский стандарт)
- `.zip` — ZIP-архив с файлами .kenml внутри

### Требования к файлам
- Максимальный размер файла: 50 MB
- В ZIP-архиве допускается только один файл .kenml на корневом уровне или во вложенных папках
- Файл должен соответствовать спецификации KENML

## Статусы обработки

После загрузки документ проходит следующие статусы:

| Статус | Описание |
|--------|----------|
| NEW | Документ загружен, ожидает обработки |
| PROCESSING | Документ в процессе анализа |
| DONE | Анализ завершён успешно |
| ERROR | Ошибка при обработке |
| SENT | Результат отправлен обратно (при использовании callback_url) |

## Получение результата

### Вариант 1: Callback URL

Если при отправке указан `callback_url`, результат анализа будет отправлен POST-запросом на этот адрес с:
- `document_id` — ID документа в системе ДРВЦ
- `status` — статус обработки (`completed` или `error`)
- `file` — ZIP-архив с полным отчётом анализа

### Вариант 2: Проверка статуса

По договорённости с администратором можно получить статус по document_id через отдельный endpoint (уточняйте у администратора).

## Требования к наименованию банка (bank_name)

Для корректной идентификации проекта рекомендуется использовать следующий формат:
```
[Наименование банка] - [Название проекта/объекта]
```

Примеры:
- `Банк Развития Казахстана - Административное здание Астана`
- `Народный Банк - Филиал Алматы`
- `Kaspi Bank - Головной офис`

## Контакты поддержки

При возникновении вопросов или проблем:
- Email: support@drvc.kz
- Телефон: +7 (7172) XX-XX-XX

## Часто задаваемые вопросы

**В: Можно ли отправить смету вместо ПСД?**
О: Да, укажите `doc_type=SMETA`.

**В: Как узнать, что анализ завершён?**
О: Используйте callback_url или обратитесь к администратору для настройки уведомлений.

**В: Можно ли отправить несколько файлов одним запросом?**
О: Да, упакуйте их в ZIP-архив.

**В: Что делать при ошибке 413 (Payload Too Large)?**
О: Разделите данные на несколько файлов или уменьшите размер архива.

---

*Документ актуален на 15.04.2024. При изменениях API будет выслано уведомление.*
