'''
A small utility to fetch preprints that have been published by a specific publisher identified by its doi prefix.
It uses the biorXiv API for publishers: https://api.biorxiv.org/publisher/help
'''

import argparse
import requests
from datetime import date
import time
from typing import List
from .utils import resolve, progress
from .toolbox import Preprint
from . import logger


def retrieve(prefix:str, start_date:str, end_date:str) -> List[Preprint]:
    """
    Retrieves a list of preprint published by a specific publisher and posted on bioRxiv within a given time range.

    Uses the bioRxiv API endpoints for publihsers https://api.biorxiv.org/publisher/
    The format of the endpoint is https://api.biorxiv.org/publisher/[publisher prefix]/[interval]/[cursor]
    It returns a messages array and a collection.
    The 'messages' array in the output provides information about what is being displayed, including cursor value and count of items for the requested interval.
    "messages":[{"status":"ok","interval":"2018-01-01:2019-01-01","cursor":"2","count":56,"total":58}]
    The following metadata elements are included in each item of 'collection':
        biorxiv_doi
        published_doi
        preprint_title
        preprint_category
        preprint_date
        published_date
        published_citation_count

    Arguments:
        prefix (str): the doi prefix of the publisher
        start_date (str): the start date (format YYYY-MM-DD) of bioRxiv posting date range to be considered
        end_date (str): the end date (format YYYY-MM-DD) of bioRxiv posting date range to be considered

    Returns:
        List of Preprints
    """

    biorxiv_api = "https://api.biorxiv.org/publisher"
    results = []
    cursor = 0
    remaining = 1
    while remaining > 0:
        url = "/".join([biorxiv_api, prefix, start_date, end_date, str(cursor)])
        logger.info(f"bioRxiv request: {url}")
        response = requests.get(url)
        if response.status_code == 200:
            response = response.json()
            message = response['messages'][0]
            if message['status'] == 'ok':
                count = int(message['count'])
                total = int(message['total'])
                logger.info(f"response received ({count} preprints)")
                cursor += count
                remaining = total - count
                results += [Preprint(**j) for j in response['collection']]
            else:
                remaining = 0
        else:
            logger.error(f"⚠️ Problem with bioRxiv api, status_code={response.status_code}")
            remaining = 0
        time.sleep(0.1)
    return results

def details(preprints: List[Preprint]) -> List[Preprint]:
    biorxiv_details_api = "https://api.biorxiv.org/detail"
    N = len(preprints)
    for i, p in enumerate(preprints):
        doi = p.biorxiv_doi
        url = "/".join([biorxiv_details_api, doi])
        progress(i, N, f"{url}")
        response = requests.get(url)
        if response.status_code == 200:
            response = response.json()
            if response.get('collection'):
                first_match = response.get('collection')[0]
                p.corr_author = first_match.get('author_corresponding')
                p.institution = first_match.get('author_corresponding_institution')
            else:
                logger.warning(f"{url} did not retrieve any preprint!")
                p.corr_author = ""
                p.institution = ""
    return preprints # not really needed since mutable


def main():
    parser = argparse.ArgumentParser( description="Retrieves bioRxiv preprint for journal", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('prefix', nargs="?", default="10.15252", help="The prefix of the publisher.")
    parser.add_argument('--start', default='2019-01-01', help="Start date for the search (format YYYY-MM-DD)")
    parser.add_argument('--end', default=str(date.today()), help="End date for the search (format YYYY-MM-DD)")
    parser.add_argument('--delimiter', default="\t", help="Column delimiter in the output (use $'\t' syntax in bash for backslash escaped characters).")
    args = parser.parse_args()
    prefix =args.prefix
    start = args.start
    end = args.end
    delimiter = args.delimiter

    results = retrieve(prefix, start, end)
    results = details(results)

    header = delimiter.join(["biorxiv_doi", "published_doi", "category", "corr_author", "institution"])
    print(header)
    for preprint in results:
        row = delimiter.join([preprint.biorxiv_doi, preprint.published_doi, preprint.preprint_category, preprint.corr_author, preprint.institution])
        print(row)
    print(f"\nTOTAL: {len(results)}")

if __name__ == "__main__":
    main()

