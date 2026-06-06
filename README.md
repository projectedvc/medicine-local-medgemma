Как запустить:
1. В одном терминале:
  1.1 cd C:\Users\USER\Desktop\projects\medicine-local-medgemma  
  1.2 .\run_local_medgemma.bat  
  
 2. Во втором новом терминале: ngrok http 3000

Сайт на localhost или http://127.0.0.1:3000, а внешняя ссылка через ngrok есть в терминале (https://overreact-grew-cornball.ngrok-free.dev)



# Radiology AI Assistant

MVP веб-системы для поддержки врача при анализе рентгенологических изображений ОГК. Система принимает DICOM/JPEG/PNG, проверяет файл, показывает снимок, запускает AI-анализ через внешний GPU-сервер или mock-режим, формирует AI-черновик, хранит финальный текст врача отдельно и ведет журнал аудита.

**Медицинское ограничение:** результат AI является только предварительной подсказкой. Окончательное решение принимает врач.

## Что реализовано

- Авторизация по логину/паролю и 6 ролей: администратор, рентгенолог, врач-пользователь, эксперт, студент, аналитик.
- Dashboard исследований с фильтрами по статусу, типу и датам.
- Загрузка DICOM/JPEG/PNG с проверкой формата, размера, читаемости и DICOM PixelData.
- Viewer: масштаб, панорамирование мышью, яркость, контраст, heatmap overlay.
- AI-анализ: ручной или авто после загрузки, confidence threshold, скрытие класса при низкой уверенности.
- Черновик описания и финальный текст врача хранятся отдельно.
- Feedback врача: false positive, false negative, wrong region, other.
- Справочник патологий ОГК.
- Журнал аудита: вход, загрузка, проверка, AI, черновик, правки, подтверждение, экспорт.
- Экспорт подтвержденного заключения в PDF/DOCX.
- Подключение GPU-сервера jupiter через `AI_SERVICE_URL`.

## Демо-пользователи

| Роль | Логин | Пароль |
| --- | --- | --- |
| Администратор | `admin` | `admin123` |
| Рентгенолог | `radiologist` | `radio123` |
| Врач-пользователь | `doctor` | `doctor123` |
| Эксперт | `expert` | `expert123` |
| Студент | `student` | `student123` |
| Аналитик | `analyst` | `analyst123` |

## Быстрый запуск через Docker

```powershell
cd C:\Users\USER\Desktop\projects\medicine
Copy-Item .env.example .env
docker compose up --build
```

После запуска:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Swagger: http://localhost:8000/docs

## Локальный запуск без Docker

Backend:

```powershell
cd C:\Users\USER\Desktop\projects\medicine\backend
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd C:\Users\USER\Desktop\projects\medicine\frontend
npm install
npm run dev
```

## Подключение GPU-сервера jupiter

В `medicine\.env` для Docker или `medicine\backend\.env` для локального backend укажите адрес inference API:

```env
AI_SERVICE_URL=http://jupiter:8899
AI_ALLOW_MOCK=false
AI_CONFIDENCE_THRESHOLD=0.70
```

Если используется Jupyter proxy, можно указать полный base URL, например:

```env
AI_SERVICE_URL=http://172.26.230.20:8000/user/student1/proxy/8899
```

Backend отправляет файл на `POST {AI_SERVICE_URL}/predict` как `multipart/form-data` с полем `file`.
Если Jupiter API работает как показанный notebook-сервер, укажите полный путь `AI_SERVICE_URL=https://shiny-net-slimy.ngrok-free.dev/generate`; backend отправит `multipart/form-data` с полями `prompt` и `image` и разберет JSON из поля `response`.

Ожидаемый ответ jupiter:

```json
{
  "prediction": "pneumonia",
  "confidence": 0.88,
  "top3": {
    "pneumonia": 0.88,
    "normal": 0.09,
    "pleural_effusion": 0.03
  },
  "heatmap_url": null
}
```

Поддерживаемые классы: `normal`, `pneumonia`, `pleural_effusion`, `pneumothorax`, `atelectasis`. Можно также возвращать русские названия, backend их нормализует.

Если `AI_ALLOW_MOCK=true`, проект работает без GPU-сервера и возвращает демонстрационный результат. Для пилота с медицинскими данными mock нужно отключить.

## Основной workflow

1. Войти как `radiologist / radio123`.
2. Создать исследование и выбрать DICOM/JPEG/PNG.
3. При включенном `Авто AI после загрузки` система сразу проверит файл, запустит AI и создаст черновик.
4. Врач просматривает снимок, редактирует финальный текст и нажимает `Подтвердить`.
5. После подтверждения доступен экспорт PDF/Word.

## Важные файлы

- `backend/app/main.py` - FastAPI приложение.
- `backend/app/models` - SQLAlchemy модели.
- `backend/app/api/routes` - API маршруты.
- `backend/app/services/ai_client.py` - интеграция с jupiter.
- `backend/app/services/image_validation.py` - проверка DICOM/JPEG/PNG.
- `frontend/src/App.tsx` - рабочий интерфейс.
- `docker-compose.yml` - запуск frontend/backend/PostgreSQL.
- `JUPITER_DEPLOY.md` - правильный запуск Jupiter + ngrok + Vercel proxy.
