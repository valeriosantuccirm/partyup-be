from typing import Any, Dict, List


def find_by_attr(
    source: List[str] = [],
    size: int = 1,
    **kwargs,
) -> Dict[str, Any]:
    must_clauses: List[Dict[str, Dict[str, Any]]] = []
    must_clauses.extend(
        [
            {
                "term": {k: v},
            }
            for k, v in kwargs.items()
        ]
    )
    q: Dict[str, Any] = {
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
