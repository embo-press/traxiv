'''
A small utility to fetch preprints that have been published by a specific publisher identified by its doi prefix.
It uses the biorXiv API for publishers: https://api.biorxiv.org/publisher/help
'''

import argparse
import requests
from datetime import date
import time
from typing import List
from .utils import resolve
from .toolbox import Preprint


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
        print("bioRxiv request:", url)
        response = requests.get(url)
        if response.status_code == 200:
            response = response.json()
            message = response['messages'][0]
            if message['status'] == 'ok':
                count = int(message['count'])
                total = int(message['total'])
                cursor += count
                remaining = total - count
                results += [Preprint(**j) for j in response['collection']]
            else:
                remaining = 0
        else:
            print(f'⚠️ Problem with bioRxiv api, status_code={response.status_code}')
            remaining = 0
        time.sleep(0.1)
    return results

def main():
    parser = argparse.ArgumentParser( description="Retrieves bioRxiv preprint for journal")
    parser.add_argument('prefix', nargs="?", default="10.15252", help="The prefix of the publisher.")
    parser.add_argument('--start', default='2019-01-01', help="Start date for the search (format YYYY-MM-DD)")
    parser.add_argument('--end', default=str(date.today()), help="End date for the search (format YYYY-MM-DD)")
    args = parser.parse_args()
    prefix =args.prefix
    start = args.start
    end = args.end
    results = retrieve(prefix, start, end)

    print("biorxiv_doi\tpublished_doi\tcategory")
    for preprint in results:
        print(preprint.biorxiv_doi, preprint.published_doi, preprint.preprint_category)

if __name__ == "__main__":
    main()

