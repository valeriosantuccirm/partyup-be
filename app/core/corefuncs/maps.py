from typing import Any

from app.core import common
from core.datamodels.schemas.response import MapsLocation


async def search_location(
    q: str,
) -> list[MapsLocation]:
    results: list[MapsLocation] = []
    data: list[dict[str, Any]] = await common.search_map_location(query=q)
    if data:
        return [MapsLocation(**place) for place in data]
    return results
