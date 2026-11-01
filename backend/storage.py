from minio import Minio
from config import MINIO_CONFIG

minio_client = Minio(**MINIO_CONFIG)

# получаем изображение из minio
def get_image(image_key: str):
    response = minio_client.get_object(
        bucket_name="products",
        object_name=image_key
    )

    try:
        image_bytes = response.read()

        content_type = response.headers.get(
            "Content-Type",
            "application/octet-stream"
        )

        return image_bytes, content_type

    finally:
        response.close()
        response.release_conn()