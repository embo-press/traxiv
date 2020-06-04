"""
Removes all the hypothes.is posts linked to a user and group and purges the collection in the MongoDB database.
"""

import argparse
import os
from . import HYPO, HYPOTHESIS_USER
from .utils import progress, get_groupid


def purge(user, groupid: str, limit: int):
    """
    A simple function to remove posts in a specific group. The posts are also removed from the MongoDB database.

    Arguments:
        groupid (str): the is of the hypothes.is group
        limit (int): the maximum number of posts to be deleted
    """

    response = HYPO.annotations.search(user=user, group=groupid, limit=limit)
    response = response.json()
    total = response['total']
    documents = response['rows']
    print(f'deleting {total} posts from {groupid} of {user}')
    delete_count = 0
    N = len(documents)
    for i, d in enumerate(documents):
        id = d['id']
        progress(i, N, f"{id}  ")
        response = HYPO.annotations.delete(id)
        if response.status_code == 200:
            delete_count += 1
    print(f"Purged {delete_count} records from {groupid}")
    print(f"{total - delete_count} remaining")


def main():
    parser = argparse.ArgumentParser( description="Removes posts and purges the database", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('group', default='', help='Name of the hypothesis group')
    parser.add_argument('--limit', default=200, help='Maximum number deleted.')

    args = parser.parse_args()
    group_name = args.group
    limit = args.limit
    groupid = get_groupid(group_name, document_uri="https://www.biorxiv.org") # important to add uri to retrieve public groups!
    if groupid:
        purge(HYPOTHESIS_USER, groupid, limit=limit)
    else:
        print(f"Could not find group: {group_name}")

if __name__ == "__main__":
    main()