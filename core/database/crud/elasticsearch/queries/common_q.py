from typing import Any


def find_by_attr(
    source: list[str] = [],
    size: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    must_clauses: list[dict[str, dict[str, Any]]] = []
    must_clauses.extend(
        [
            {
                "term": {k: v},
            }
            for k, v in kwargs.items()
        ]
    )
    q: dict[str, Any] = {
        "query": {
            "bool": {
                "must": must_clauses,
            }
        },
        "size": size,
    }
    if source:
        q["_source"] = source
    return q
