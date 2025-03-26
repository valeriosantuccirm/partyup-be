from typing import List

from app.core import common
from app.datamodels.schemas.response import MapsLocation


async def search_location(
    user_input: str,
) -> List[MapsLocation]:
    results: List[MapsLocation] = []
    data: List[common.Dict[str, common.Any]] = await common.search_map_location(
        query=user_input
    )
    if data:
        return [MapsLocation(**place) for place in data]
    return results
