"""Bounded dataset reads and durable JSON files shared by the agent recipes."""
import json
import os
from pathlib import Path


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def bounded_items(dataset, *, page_size=25, max_pages=4):
    """Fail before returning a partial dataset, so callers cannot advance state."""
    if not 1 <= page_size <= 1000 or not 1 <= max_pages <= 100:
        raise ValueError('page_size must be 1..1000; max_pages must be 1..100')
    rows = []
    # Dataset.get().itemCount can lag after SUCCEEDED; read actual items instead.
    for index in range(max_pages):
        offset = index * page_size
        page = dataset.list_items(offset=offset, limit=page_size, clean=True)
        total = page.total
        if total > page_size * max_pages:
            raise ValueError('Dataset exceeds page budget; raise the budget and resume the saved run')
        rows.extend(page.items)
        if total > len(rows) and len(page.items) < page_size:
            raise ValueError('Dataset ended before the reported total')
        if len(page.items) < page_size or (total == len(rows) and total > 0):
            return rows
    raise ValueError('Cannot prove dataset complete within page budget; increase max_pages and resume')
