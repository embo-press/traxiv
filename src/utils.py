"""
A few simple utility fuctions.
"""

import requests
from typing import Dict
from . import HYPO

DOI_ORG = "https://doi.org"

def get_groupid(group_name: str, document_uri: str='') -> str:
    """
    Find the hypothes.is identifier for a group with a given name.
    If several groups have the same name, the id of the first group returned by the hypothes.is API is returned.
    To retreive a public group, a document uri should be provided that is within the scope of the group.

    Arguments:
        group_name: the name of the group.
        document_uri (str): a document uri within the scope of the group; important to retrieved public groups

    Returns:
        str: the group id
    """

    groupid = ''
    if group_name == '__world__':
        groupid = '__world__'
    else:
        group_list = HYPO.groups.get_list().json() # this gets only private groups but NOT the public groups
        group_list += HYPO.groups.get_list(document_uri=document_uri).json() # to retrieve public restricted groups, a url within the scope of the group should be provided
        for g in group_list:
            if g['name'] == group_name:
                groupid = g['id']
                break
    return groupid


def resolve(doi:str) -> str:
    """
    Resolves a doi using doi.org

    Arguments:
        doi (str): the...doi.

    Returns:
        str: the url to which the doi resolves to.
    """
    response = requests.get(f"{DOI_ORG}/{doi}")
    if response.status_code:
        link = response.url
    else:
        link = ''
    return link


def info(doi: str) -> Dict:
    """
    Retreives some metadat from CrossRef for a paper.

    Arguments:
        doi (str): the doi of the paper.

    Returns:
        Dict: the full json response returned by CrossRef.
    """
    headers = {"Accept": "application/json"}
    response = requests.get(f"{DOI_ORG}/{doi}", headers=headers)
    if response.status_code == 200:
        crossref_json =  response.json()
    else:
        crossref_json = {}
    return crossref_json


def progress(count: int, total: int, status: str=''):
    """
    A progress bar.

    Arguments:
        count (int): the current progress counter.
        total (int): the total number of items.
        status (str): a dynamic message to be displayed next to the progress bar.
    """
    # From https://gist.github.com/vladignatyev/06860ec2040cb497f0f3
    # The MIT License (MIT)
    # Copyright (c) 2016 Vladimir Ignatev
    #
    # Permission is hereby granted, free of charge, to any person obtaining
    # a copy of this software and associated documentation files (the "Software"),
    # to deal in the Software without restriction, including without limitation
    # the rights to use, copy, modify, merge, publish, distribute, sublicense,
    # and/or sell copies of the Software, and to permit persons to whom the Software
    # is furnished to do so, subject to the following conditions:
    #
    # The above copyright notice and this permission notice shall be included
    # in all copies or substantial portions of the Software.
    #
    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
    # INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
    # PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
    # FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT
    # OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
    # OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    if count == 0:
        print()
    bar_len = 60
    filled_len = int(round(bar_len * (count+1) / float(total)))
    percents = round(100.0 * (count+1) / float(total))
    bar = '█' * filled_len + '-' * (bar_len - filled_len)
    print('\r[%s] %s%s ...%s' % (bar, percents, '%', status), end="\r", flush=True)
    if count == total-1:
        print("\n")
