from typing import Any

from app.core import common
from app.datamodels.schemas.response import MapsLocation


async def search_location(
    user_input: str,
) -> list[MapsLocation]:
    results: list[MapsLocation] = []
    data: list[dict[str, Any]] = await common.search_map_location(query=user_input)
    if data:
        return [MapsLocation(**place) for place in data]
    return results
