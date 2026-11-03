# Product Catalog — Telegram Mini App

Каталог товаров с фотографиями, доступный в браузере и внутри Telegram. Администратор добавляет товар через Telegram-бота: отправляет фотографию с названием в подписи, после чего товар сохраняется и появляется в каталоге.

## Демо

- **Каталог:** https://test-catalog-web.vercel.app
- **Telegram-бот:** https://t.me/my_product_catalog_bot
- **API / Swagger:** https://danaya-test-catalog-api.duckdns.org/docs
- **Проверка API:** https://danaya-test-catalog-api.duckdns.org/health

Добавление товаров доступно только Telegram-пользователю с ID, указанным в `ADMIN_TELEGRAM_ID`. Просмотр каталога публичный.

## Возможности

- Добавление товара фотографией с подписью через Telegram-бота (`/add`).
- Проверка Telegram ID администратора и защита `POST /products` ключом API.
- Хранение информации о товарах в PostgreSQL, изображений — в MinIO.
- Просмотр товаров в адаптивном Next.js-каталоге, в том числе через Telegram Mini App.
- Кнопка «Обновить» для получения новых товаров без полной перезагрузки страницы.
- Два режима запуска бота: `polling` для локальной разработки и `webhook` для сервера.
- Два экземпляра FastAPI и два webhook-экземпляра бота в production, распределение запросов через Caddy.

## Стек и архитектура

| Компонент | Технологии |
| --- | --- |
| Веб-каталог | Next.js (App Router), React, TypeScript |
| API | FastAPI, Python, asyncpg |
| Telegram-бот | aiogram 3, aiohttp, httpx |
| База данных | PostgreSQL (локально в Docker, в production — Neon) |
| Файловое хранилище | MinIO |
| Reverse proxy, HTTPS, балансировка | Caddy |
| Контейнеризация | Docker Compose |
| Развёртывание | AWS EC2 (API, бот, MinIO, Caddy), Vercel (Next.js) |

```text
Пользователь ──► Next.js (Vercel) ──► Caddy ──► FastAPI #1 / #2
                                         │             │
                                         │             ├──► PostgreSQL (Neon)
Telegram ──webhook──► Caddy ──► Bot #1 / #2             └──► MinIO
                                  │
                                  └──► Caddy (внутренний HTTP :8080)
                                            └──► FastAPI #1 / #2
```

При чтении списка товаров FastAPI возвращает ссылки на изображения через собственный endpoint. MinIO не требуется открывать для публичного доступа: изображения отдаются через API.

## Структура проекта

```text
backend/          FastAPI, работа с PostgreSQL и MinIO, SQL-схема
bot/              Telegram-бот, polling и webhook
frontend/         Next.js-каталог
caddy/Caddyfile   Публичный reverse proxy и балансировка
compose.yaml      Локальные PostgreSQL и MinIO
compose.prod.yaml Серверные MinIO, API x2, bot x2 и Caddy
.env.example      Пример переменных окружения
```

## Локальный запуск

Требуются Docker и Docker Compose, Python 3.14, Node.js и pnpm. Команды ниже рассчитаны на запуск из корня репозитория; Python-компоненты используют отдельные виртуальные окружения, поскольку их зависимости зафиксированы независимо.

### 1. Настройка окружения и хранилищ

Скопируйте `.env.example` в `.env` и замените значения-заглушки на свои. Для локального запуска нужны:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST=127.0.0.1`, `POSTGRES_PORT=5433`;
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_ENDPOINT=127.0.0.1:9010`;
- `BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `INTERNAL_API_KEY`;
- `API_URL=http://127.0.0.1:8000`, `BOT_MODE=polling`, `WEBAPP_URL` (HTTPS-адрес каталога).

Для локальной PostgreSQL не задавайте `DATABASE_URL`: при наличии этой переменной FastAPI использует указанный DSN вместо параметров локальной БД.

```bash
docker compose up -d
```

Локальный `compose.yaml` поднимает **только PostgreSQL и MinIO**. SQL-файл `backend/schema.sql` автоматически применяется PostgreSQL при **первом создании пустого тома данных**.

Откройте MinIO Console по адресу http://127.0.0.1:9011, войдите с `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` и **создайте бакет `products`**. Он не создаётся автоматически, а для загрузки изображений необходим. Публичный доступ к бакету включать не нужно.

> Не выполняйте `docker compose down -v`, если нужно сохранить данные: эта команда удаляет тома PostgreSQL и MinIO.

### 2. FastAPI

В отдельном терминале:

```bash
cd backend
python -m venv .venv
# Windows / Git Bash:
source .venv/Scripts/activate
# Linux / macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

API: http://127.0.0.1:8000; Swagger UI: http://127.0.0.1:8000/docs.

### 3. Telegram-бот

В другом терминале:

```bash
cd bot
python -m venv .venv
# Windows / Git Bash:
source .venv/Scripts/activate
# Linux / macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Локально используется `BOT_MODE=polling`. **Для параллельной разработки используйте отдельного тестового Telegram-бота.** Если тот же `BOT_TOKEN` уже зарегистрирован на сервере с webhook, локальный polling не будет получать обновления. Переключать production-бота ради локального запуска не рекомендуется.

Администратор отправляет `/add`, затем одно фото с названием товара в подписи.

### 4. Next.js

Создайте `frontend/.env.local`:

```dotenv
CATALOG_API_URL=http://127.0.0.1:8000
```

В отдельном терминале:

```bash
cd frontend
pnpm install
pnpm dev
```

Откройте http://localhost:3000. URL API используется серверной частью Next.js. Новый товар появляется после открытия страницы или нажатия кнопки «Обновить».

## HTTP API

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| `GET` | `/health` | Проверка работы процесса FastAPI |
| `GET` | `/products` | Список товаров и URL изображений |
| `GET` | `/products/{product_id}/image` | Получение изображения через API |
| `POST` | `/products` | Создание товара; заголовок `X-API-Key` |

`POST /products` принимает `multipart/form-data` с полями `name` и `image`. Поддерживаются JPEG, PNG и WebP размером до 5 МБ. Название — от 1 до 200 символов после удаления пробелов по краям. Неавторизованный запрос возвращает `401`.

Пример локального запроса:

```bash
curl -X POST http://127.0.0.1:8000/products \
  -H "X-API-Key: YOUR_INTERNAL_API_KEY" \
  -F "name=Тестовый товар" \
  -F "image=@./photo.jpg"
```

В обычном пользовательском сценарии этот запрос отправляет Telegram-бот, поэтому ключ API не передаётся браузеру.

## Production-развёртывание

Серверный состав описан в `compose.prod.yaml`. В нём **нет локального контейнера PostgreSQL**: используется внешний Neon PostgreSQL.

1. Создайте PostgreSQL-базу в Neon и примените к ней SQL из `backend/schema.sql` (например, через Neon SQL Editor).
2. Подготовьте сервер с Docker Compose. Домен `API_DOMAIN` должен указывать на его публичный IP; откройте входящие TCP-порты 80 и 443 для Caddy.
3. Создайте на сервере `.env` по образцу `.env.example` и задайте реальные секреты и настройки, включая `DATABASE_URL`, `BOT_TOKEN`, `ADMIN_TELEGRAM_ID`, `INTERNAL_API_KEY`, MinIO credentials, `BOT_MODE=webhook`, `WEBHOOK_URL`, `WEBHOOK_SECRET`, `WEBAPP_URL` и `API_DOMAIN`.
4. Запустите MinIO и создайте бакет `products` до отправки фотографий.
5. Запустите серверные сервисы:

```bash
docker compose -f compose.prod.yaml up -d --build
```

6. На Vercel импортируйте этот репозиторий, укажите Root Directory `frontend`, Framework Next.js и переменную окружения:

```dotenv
CATALOG_API_URL=https://danaya-test-catalog-api.duckdns.org
```

7. В Telegram настройте кнопку открытия Mini App на HTTPS-адрес каталога. При запуске webhook-бот регистрирует `WEBHOOK_URL` через Telegram Bot API; Caddy маршрутизирует `/telegram/webhook` в webhook-экземпляры бота.

Для безопасного доступа к MinIO Console на сервере используйте SSH-туннель, не публикуя порты MinIO в интернет. В `compose.prod.yaml` MinIO доступен на `127.0.0.1:9011` хоста (консоль). Пример с локальным портом 19011:

```bash
ssh -L 19011:127.0.0.1:9011 ubuntu@SERVER_IP
```

После этого консоль доступна на http://127.0.0.1:19011. Способ SSH-аутентификации зависит от настроек сервера.

Для обновления развёртывания после `git pull`:

```bash
docker compose -f compose.prod.yaml up -d --build
```

## Масштабирование и проверка отказа

В production запущены два независимых экземпляра FastAPI (`api`, `api2`) и два экземпляра Telegram webhook-сервера (`bot`, `bot2`). Caddy применяет round-robin и проверки `/health`. Все экземпляры API используют одну PostgreSQL-базу и одно MinIO-хранилище; состояние каталога не хранится в памяти отдельных процессов.

Практически проверены сценарии остановки первого API и первого webhook-бота: новые запросы продолжили обрабатываться оставшимися экземплярами, включая загрузку фотографий и просмотр каталога.

Для повторения проверки на сервере (поочерёдно, **не останавливайте оба экземпляра одной роли**):

```bash
docker compose -f compose.prod.yaml stop api
# Проверить /health, каталог и добавление товара

docker compose -f compose.prod.yaml start api

docker compose -f compose.prod.yaml stop bot
# Проверить /start, /add и добавление товара

docker compose -f compose.prod.yaml start bot
```

**Ограничения:** это отказоустойчивость на уровне экземпляров приложений, а не инфраструктуры целиком. Caddy, EC2 и MinIO на одном сервере остаются едиными точками отказа. При падении webhook-процесса во время уже принятого события его обработка может не завершиться; гарантированной очереди/повторной обработки и идемпотентности добавления товаров здесь нет. Проверка `/health` подтверждает работу процесса, но не полную доступность зависимых сервисов. Для полноценного HA нужны дополнительные компоненты и репликация.

## Безопасность

- `POST /products` защищён заголовком `X-API-Key`; бот разрешает добавление только пользователю с `ADMIN_TELEGRAM_ID`.
- Webhook-запросы проверяются по секретному заголовку Telegram (`WEBHOOK_SECRET`).
- MinIO не опубликован в интернет; изображения выдаёт FastAPI.
- `.env`, токены и ключи доступа не должны попадать в Git. В репозитории находится только `.env.example` с заглушками.

## Примечание

Проект создан как техническое тестовое задание. Для демонстрации и проверки используется небольшое развёртывание на одной виртуальной машине; ограничения архитектуры перечислены выше.
