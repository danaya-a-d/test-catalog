from fastapi import FastAPI

app = FastAPI()

products = [
             {
               "id": 1,
               "name": "Клавиатура",
               "image_url": "https://example.com/keyboard.jpg"
             },
             {
               "id": 2,
               "name": "Мышь",
               "image_url": "https://example.com/mouse.jpg"
             }
           ]


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/products")
async def get_products():
    return products