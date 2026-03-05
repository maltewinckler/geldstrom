from fastapi import APIRouter, Request

router = APIRouter(prefix="/webhooks")


@router.post("/paypal")
async def paypal_webhook(request: Request) -> dict:
    # TODO: 1. Extract PayPal signature headers
    # TODO: 2. Verify signature via PayPal Notifications API
    # TODO: 3. Parse event_type from body
    # TODO: 4. Idempotency check (processed_webhook_events table)
    # TODO: 5. Dispatch: ACTIVATED → activate_key, CANCELLED/SUSPENDED → deactivate_key
    # TODO: 6. Record event_id, return response
    return {"received": True}
