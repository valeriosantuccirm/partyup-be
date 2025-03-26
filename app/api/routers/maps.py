from typing import Annotated, List

from fastapi import APIRouter, Query
from pydantic import StrictStr
from starlette import status

from app.core.corefuncs import maps

router = APIRouter(prefix="/maps")


@router.get(
    path="/location/search",
    status_code=status.HTTP_200_OK,
    response_model=List[maps.MapsLocation],
    description="Search for locations based on user input.",
)
async def search_location(
    user_input: Annotated[StrictStr, Query(default=...)],
) -> List[maps.MapsLocation]:
    """
    Search for locations based on user input.

    Args:
        user_input (StrictStr): The search term for the location.

    Returns:
        List[MapsLocation]: A list of matched locations.
    """
    return await maps.search_location(user_input=user_input)
