import asyncpg
from config import DB_CONFIG

# получаем список товаров из бд
async def fetch_products():
    connection = await asyncpg.connect(**DB_CONFIG)

    try:
        rows = await connection.fetch(
            "SELECT id, name, image_key FROM products ORDER BY id"
        )
        return [dict(row) for row in rows]

    finally:
        await connection.close()


# добавляем новый товар в бд и возвращаем информации о нем
async def insert_product(name: str, image_key: str):
    connection = await asyncpg.connect(**DB_CONFIG)

    try:
        row = await connection.fetchrow(
            """
            INSERT INTO products (name, image_key)
            VALUES ($1, $2)
            RETURNING id, name, image_key, created_at
            """,
            name,
            image_key
        )

        return dict(row)

    finally:
        await connection.close()


# находим ключ изображения в бд
async def fetch_product_image_key(product_id: int):
    connection = await asyncpg.connect(**DB_CONFIG)

    try:
        return await connection.fetchval(
            "SELECT image_key FROM products WHERE id = $1",
            product_id
        )
    finally:
        await connection.close()