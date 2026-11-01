from secrets import compare_digest

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from config import INTERNAL_API_KEY

# извлечение api ключа из заголовка
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)

# проверка ключа
def verify_api_key(
    key: str | None = Depends(api_key_header)
):
    if key is None or not compare_digest(
        key, INTERNAL_API_KEY
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized"
        )