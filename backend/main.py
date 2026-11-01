import logging
from uuid import uuid4
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request, Depends
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from db import fetch_products, insert_product, fetch_product_image_key
from storage import get_image, minio_client
from minio.error import S3Error
from auth import verify_api_key

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/products")
async def get_products(request: Request):
    products = await fetch_products()

    for product in products:
        product["image_url"] = str(
            request.url_for(
                "get_product_image",
                product_id=product["id"]
            )
        )

    return products


@app.post(
    "/products",
    status_code=201,
    dependencies=[Depends(verify_api_key)]
)
async def create_product(
    name: str = Form(),
    image: UploadFile = File()
):
    name = name.strip()

    if not name or len(name) > 200:
        raise HTTPException(
            status_code=400,
            detail="Название должно содержать от 1 до 200 символов"
        )

    # проверяем формат изображения
    extensions = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp"
    }

    extension = extensions.get(image.content_type)

    if extension is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image type"
        )

    # проверяем размер изображения
    max_size = 5 * 1024 * 1024

    if image.size is None or not (0 < image.size <= max_size):
        raise HTTPException(
            status_code=400,
            detail="Invalid image size"
        )

    # генерируем уникальное имя изображения
    image_key = f"{uuid4().hex}.{extension}"

    # загружаем изображение в minio
    try:
        await run_in_threadpool(
            minio_client.put_object,
            bucket_name="products",
            object_name=image_key,
            data=image.file,
            length=image.size,
            content_type=image.content_type
        )
    except Exception as exc:
        logger.exception("MinIO upload failed")
        raise HTTPException(
            status_code=503,
            detail="Не удалось сохранить изображение"
        ) from exc

    # загружаем изображение в бд
    try:
        product = await insert_product(name, image_key)
        return product

    except Exception as exc:
        logger.exception("Product insert failed")

        # если запись в бд не удалась, удаляем изображение из minio
        try:
            await run_in_threadpool(
                minio_client.remove_object,
                bucket_name="products",
                object_name=image_key
            )
        except Exception:
            logger.exception("Failed to remove orphaned image")

        raise HTTPException(
            status_code=503,
            detail="Не удалось создать товар"
        ) from exc



@app.get("/products/{product_id}/image")
async def get_product_image(product_id: int):
    # находим ключ изображения в базе данных
    image_key = await fetch_product_image_key(product_id)

    if image_key is None:
        raise HTTPException(
            status_code=404,
            detail="Товар не найден"
        )

    # получаем фотографию из minio
    try:
        image_bytes, content_type = await run_in_threadpool(
            get_image,
            image_key
        )

    except S3Error as exc: # специальный обработчик ошибок minio
        if exc.code == "NoSuchKey":
            raise HTTPException(
                status_code=404,
                detail="Изображение не найдено"
            ) from exc

        logger.exception("MinIO read failed")
        raise HTTPException(
            status_code=503,
            detail="Ошибка получения изображения"
        ) from exc

    except Exception as exc:
        logger.exception("Image retrieval failed")
        raise HTTPException(
            status_code=503,
            detail="Ошибка получения изображения"
        ) from exc

    # возвращаем изображение браузеру
    return Response(
        content=image_bytes,
        media_type=content_type,
        headers={"X-Content-Type-Options": "nosniff"}
    )
