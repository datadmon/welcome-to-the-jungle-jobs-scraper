"""Load job JSON as real LangChain Documents without an LLM or embedding API."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

from common import bounded_items
from config import ACTOR, BOARD


def compact(value):
    if isinstance(value, dict):
        return str(value.get('name') or value.get('title') or json.dumps(value, ensure_ascii=False))
    if isinstance(value, list):
        return ', '.join(compact(v) for v in value)
    return '' if value is None else str(value)


class JobDocumentLoader(BaseLoader):
    """Fixture or a completed Apify dataset -> cited documents with stable IDs."""

    def __init__(self, rows=None, *, dataset=None, page_size=25, max_pages=4):
        if (rows is None) == (dataset is None):
            raise ValueError('Supply exactly one of rows or dataset')
        self.rows, self.dataset = rows, dataset
        self.page_size, self.max_pages = page_size, max_pages

    def lazy_load(self):
        rows = self.rows if self.rows is not None else bounded_items(
            self.dataset, page_size=self.page_size, max_pages=self.max_pages)
        seen = set()
        for row in rows:
            source = row.get('url')
            if not isinstance(source, str) or urlparse(source).scheme not in ('https', 'http') or not urlparse(source).netloc:
                raise ValueError('A source job URL is required for citations')
            key = str(row.get('dedupKey') or f"{BOARD}:{row.get('id') or source}")
            if key in seen:
                continue
            seen.add(key)
            date = row.get('postedAt') or row.get('publishedAt') or 'not supplied'
            scraped = row.get('scrapedAt') or 'not supplied'
            fields = {
                'Title': row.get('title'),
                'Company': row.get('company') or row.get('companyName'),
                'Locations': row.get('locations') or row.get('locationText') or row.get('city'),
                'Skills': row.get('skills'),
                'Salary as published': row.get('salaryText') or row.get('salary') or 'not disclosed',
                'Salary minimum LPA': row.get('salaryMinLpa'),
                'Salary maximum LPA': row.get('salaryMaxLpa'),
                'Description': row.get('description') or row.get('summary'),
            }
            text = '\n'.join(f'{k}: {compact(v)}' for k, v in fields.items() if v is not None)
            text += f'\nBoard: {BOARD}\nPosted: {date}\nRetrieved: {scraped}\nSource: {source}'
            yield Document(id=key, page_content=text, metadata={
                'source': source, 'board': BOARD, 'posted_at': date,
                'scraped_at': scraped, 'actor': ACTOR, 'job_id': str(row.get('id', '')),
                'citation': f"[{compact(row.get('title'))}]({source}) ({BOARD}; posted {date})",
            })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=Path(__file__).parents[1] / 'sample-output.json')
    parser.add_argument('--dataset', help='Read an existing completed dataset; starts no Actor')
    parser.add_argument('--page-size', type=int, default=25)
    parser.add_argument('--max-pages', type=int, default=4)
    args = parser.parse_args()
    if args.dataset:
        from apify_client import ApifyClient
        dataset = ApifyClient(os.environ['APIFY_TOKEN']).dataset(args.dataset)
        loader = JobDocumentLoader(dataset=dataset, page_size=args.page_size, max_pages=args.max_pages)
    else:
        loader = JobDocumentLoader(json.loads(args.fixture.read_text(encoding='utf-8')))
    documents = loader.load()
    print(json.dumps([{'id': d.id, 'page_content': d.page_content, 'metadata': d.metadata} for d in documents], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
