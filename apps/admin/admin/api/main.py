from fastapi import FastAPI

from admin.api.webhooks.paypal import router as paypal_router

app = FastAPI()
app.include_router(paypal_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
