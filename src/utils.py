from itertools import chain, repeat, starmap
from typing import Any, Iterable, Mapping


def uncompress(it: Iterable[tuple[Any, int]]) -> Iterable[Any]:
    return chain.from_iterable(starmap(repeat, it))


def parse_dict(dct: Mapping[str, str]) -> dict[str, int | float | str]:
    def parse_field(f: str) -> int | float | str:
        try:
            return int(f)
        except Exception:
            try:
                return float(f)
            except Exception:
                return f

    return {k: parse_field(f) for k, f in dct.items()}
