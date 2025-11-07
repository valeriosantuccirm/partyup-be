from fastapi import FastAPI
from pydantic import BaseModel, Field, StrictStr
from run_daily_payments import run_daily_payments
from starlette import status

from producer.enums.common import ResponseStatus

app = FastAPI(
    title="Daily Payments Cloud Func",
    prefix="daily-payment",
)


class TriggerResponse(BaseModel):
    status: ResponseStatus = Field(default=ResponseStatus.OK)
    message: StrictStr = Field(default="Cloud func triggered")


@app.get(
    "/",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_daily_payments() -> TriggerResponse:
    """
    Entrypoint HTTP for GCP loud Scheduler.
    """
    try:
        await run_daily_payments()
        return TriggerResponse(
            message=f"Triggered cloud func from: {__name__}",
        )
    except Exception as e:
        return TriggerResponse(
            status=ResponseStatus.KO,
            message=f"Trigger failed due to an error: {e}",
        )


@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> dict[str, str]:
    """
    Heakth check endpoint.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        app="app.main:app",
        reload=True,
        host="0.0.0.0",
        port=8000,
        workers=os.cpu_count(),
        loop="uvloop",
        http="httptools",
        timeout_keep_alive=5,
    )
