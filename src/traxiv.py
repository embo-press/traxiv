"""
Preprint associated to paper published by a publisher are retrieved from bioRxiv. 
Links to the Review Process Files are included in a template to generate post ready for posting on hypothes.is
The pre-prepared posts are cached in a MongDB and finally posted in a specific group on hypothes.is
"""

import argparse
import requests
from datetime import date
import time
import re
from string import Template
from pprint import pprint
from typing import List, Dict
from .db import MongoPreprints
from . import HYPO, HYPOTHESIS_USER
from .biorxiv import retrieve
from .rpf import generate_rpf_link
from .utils import resolve, info, progress, get_groupid
from .toolbox import Preprint, Published, HypoPost, Target, post_one
from .template import embo_press_template, banners


MG = MongoPreprints(HYPOTHESIS_USER)


class HypoPostRPF(HypoPost):
    """
    Extends HypoPost to generate a templated annotation with tags based on the metadata of a paper and preprint.
    """

    def generate(self, preprint:Preprint, paper:Published, template:Template):
        """
        Generates the text of the post from a template based on the metadata of the target preprint and the associated published paper.
        
        Arguments:
            preprint (Preprint): the preprint to which the post is going to be linked; only used to retieve a subject category tag.
            paper (Published): the published paper, used to retrieve the link to the review process file (rpf), the journal, the doi of the paper and the link to a banner image
            template (Template): a simple string.Template object to generate the text of the annotation with appropriate substitution
        """

        banner_url = banners[paper.journal]
        self.annotation_text = template.substitute({'rpf_link': paper.rpf, 'banner': banner_url, 'paper_doi': paper.doi})
        self.tags = ['PeerReviewed', 'EMBOPress', paper.journal, preprint.preprint_category]

class PublishedWithRPF(Published):
    """
    Extends Published to add a link to the EMBO Press review process file (RPF).

    Arguments:
        rpf (str): url to the downloadable review process file.
    """
    def __init__(self, rpf: str='', *args, **kwargs):
        super(PublishedWithRPF, self).__init__(*args, **kwargs)
        self.rpf = rpf

    def from_doi(self, doi):
        """
        Extends the parent from_doi() method by creating a link to the review process file from the doi.

        Arguments:
            doi (str): the doi of the paper.
        """
        super(PublishedWithRPF, self).from_doi(doi)
        self.rpf = generate_rpf_link(self.journal, doi)


class Traxiv:
    """
    Retrieves preprints associated with a publisher, generates hypothe.is posts and caches them on MongoDB. Posts the annotations to hypothes.is

    Arguments:
        db (MongoPreprints): the object handling transactions with MongoDB.
    """

    def __init__(self, db: MongoPreprints):
        self.db = db

    def retrieve_preprints(self, prefixes: List, start_date: str, end_date: str) -> List[Preprint]:
        """
        Rerieves the list of preprint corrsponding to multiple publishers.

        Arguments:
            prefixes (List): the list of doi prefixes that identify the publishers of interest.
            start_date (str): the start date of the time range to be considered (format YYYY-MM-DD)
            end_date (str): the end date of the time range to be considered (format YYYY-MM-DD)
        """

        preprints: List[Preprint] = []
        for prefix in prefixes:
            retrieved = retrieve(prefix, start_date, end_date)
            print(f'Found {len(retrieved)} preprints from {prefix}.')
            preprints += retrieved
        return preprints

    def update(self, preprints: List[Preprint], journals: List[str]):
        """
        Prepares hypothes.is posts from a list of preprints.
        Only preprints that were not yet posted are processed.
        Only preprints that were ultimately published in the provided list of journals are kept.
        This is useful since the bioRxiv allows only to select by publisher, which may publish many journals.
        The prepareed posts are cached in the MongoDB database to be able to recover from interruptions of the biorxiv or crossref webservices.

        Arguments:
            preprints (List[Preprints]): list of preprints to process.
            journals (List): the name of the journals of interest.
        """

        N = len(preprints)
        not_updated = []
        for i, prepr in enumerate(preprints):
            progress(i, N, f"{prepr.biorxiv_doi}          ")
            pre_existing = self.db.exists(prepr.biorxiv_doi)
            if not pre_existing:
                paper_doi = prepr.published_doi
                paper = PublishedWithRPF()
                paper.from_doi(paper_doi)
                if paper.rpf and paper.journal in journals:
                    prepr.biorxiv_url = resolve(prepr.biorxiv_doi)  # relies of slow webservice, so we do it only when necessary
                    hypo_post = HypoPostRPF()
                    hypo_post.generate(prepr, paper, embo_press_template)
                    self.db.insert(prepr, paper, hypo_post)
                else:
                    not_updated.append({'doi': prepr.biorxiv_doi, 'reason': f"{'rpf issue' if not paper.rpf else ''} {'not in journals' if not paper.journal in journals else ''}"})
            else:
                not_updated.append({'doi': prepr.biorxiv_doi, 'reason': 'pre-existing'})
        if not_updated:
            print(f"{len(not_updated)} records were NOT updated:")
            pprint(not_updated)

    def post(self, groupid: str) -> int:
        """
        Retrieves prepared posts from the MongoDB and posts them on hypothesis in the specified group.

        Arguments:
            groupid (str): id of the group where the posts should be posted
        """

        permissions = HYPO.helpers.permissions(
            read=[f'group:{groupid}'],
            update=[f'acct:{HYPOTHESIS_USER}@hypothes.is'],
            delete=[f'acct:{HYPOTHESIS_USER}@hypothes.is'],
            admin=[f'acct:{HYPOTHESIS_USER}@hypothes.is']
        )
        updated = 0
        rows, N = self.db.not_yet_posted() # or to_be_updated
        for i, row in enumerate(rows):
            preprint = Preprint(**row['preprint'])
            annotation = HypoPost(**row['annotation'])
            progress(i, N, f"{preprint.biorxiv_doi}           ")
            target = Target(preprint.biorxiv_url, preprint.biorxiv_doi, preprint.preprint_title)
            response = post_one(permissions, groupid, target, annotation)
            if response.status_code == 200:
                hyp_id = response.json()['id']
            else:
                hyp_id = ''
                print(response.text)
            self.db.update(preprint.biorxiv_doi, hyp_id)
            updated += 1
            time.sleep(0.1)
        return updated

    def group_in_db(self, group_name: str) -> str:
        """
        Finds the hypothes.is id assigne to a group specified by its name and creates a corresponding MongoDB collection if it does not exist yet.

        Arguments:
            group_name (str): the name of the group.

        Returns:
            str: the hypothes.is id of the group
        """

        groupid = get_groupid(group_name, document_uri="https://www.biorxiv.org") # important to add uri to retrieve public groups!
        if groupid:
            self.db.collection(groupid)
        return groupid

    def post_all(self, group_name: str, prefixes: List[str], journals: List[str], start_date: str, end_date: str):
        """
        Retrieves preprints that were published in the specified journals and published during a specific interval of time.
        Updates the MongoDB database and posts templated annotations linking to the Review Process Files of the published paper.

        Arguments:
            group_name (str): the name of the hypothes.is group where annotations will be posted.
            prefixes (List): the list of publishers doi prefixes.
            journals (List): the list of the selected journals.
            start_date (str): the start date of the time interval (format YYYY-MM-DD).
            end_date (str): the end date of the time interval (format YYYY-MM-DD).
        """

        groupid = self.group_in_db(group_name)
        if groupid:
            print(f"Retrieving preprints for {', '.join(prefixes)} from bioRxiv.")
            preprints = self.retrieve_preprints(prefixes, start_date, end_date)

            print(f"Resolving dois and generating RPF links.")
            self.update(preprints, journals)

            print(f"Posting to hypothes.is group {groupid}")
            posted = self.post(groupid)

            print(f"Posted {posted} records")
        else:
            print(f"Could not find group: {group_name}")


def main():
    parser = argparse.ArgumentParser( description="Posts RPF files to hypothes.is ", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--prefixes', default = ['10.15252', '10.26508'], help="List of publisher's doi prefixes to retrieve corresponding preprints.")
    parser.add_argument('--journals', default = ['The EMBO Journal', 'EMBO reports', 'EMBO Molecular Medicine', 'Molecular Systems Biology', 'Life Science Alliance'], help="The journals to scan.")
    parser.add_argument('--start', default='2019-01-01', help="Start date for the search (format YYYY-MM-DD)")
    parser.add_argument('--end', default=str(date.today()), help="End date for the search (format YYYY-MM-DD)")
    parser.add_argument('--group', default='', help='Name of the hypothesis group')

    args = parser.parse_args()
    prefixes =args.prefixes
    journals = args.journals
    start_date = args.start
    end_date = args.end
    group_name = args.group

    Traxiv(MG).post_all(group_name, prefixes, journals, start_date, end_date)

if __name__ == "__main__":
    main()