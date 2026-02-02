from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import StrictStr
from starlette import status

from app.core.corefuncs import maps
from app.core.decorators import manage_transaction
from core.datamodels.schemas.response import MapsLocation

router = APIRouter(prefix="/locations")


@router.get(
    path="/autocomplete",
    status_code=status.HTTP_200_OK,
    response_model=list[str],
    description="Search for locations based on user input.",
)
@manage_transaction
async def search_location(
    q: Annotated[StrictStr, Query(default=...)],
) -> list[str]:
    """
    Search for locations based on user input.

    Args:
        q (StrictStr): The search term for the location.

    Returns:
        List[MapsLocation]: A list of matched locations.
    """
    results: list[MapsLocation] = await maps.search_location(q=q)
    return [f"{r.display_name} - ({r.lat}, {r.lon})" for r in results]
