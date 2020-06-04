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
from . import HYPO, HYPOTHESIS_USER
from .biorxiv import retrieve
from .rpf import generate_rpf_link
from .utils import resolve, info, progress, get_groupid
from .toolbox import Preprint, Published, HypoPost, Target, post_one, exists
from .template import embo_press_template, banners


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
    Retrieves preprints associated with a publisher, generates hypothe.is posts and posts the annotations to hypothes.is

    Arguments:
        group_name (str): the name of the hypothesis group
    """

    def __init__(self, group_name: str):
        self.group_name = group_name
        self.groupid = get_groupid(self.group_name, document_uri="https://www.biorxiv.org") # important to add uri to retrieve public groups!
        if self.groupid:
            print(f"Group {self.group_name} has groupid {self.groupid}")
        else:
            print(f"Could not find groupid for group: {group_name}")
            print(f"Nothing can be posted.")


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

    def generate(self, preprints: List[Preprint], journals: List[str]) -> List[Dict[HypoPostRPF, Target]]:
        """
        Prepares hypothes.is posts from a list of preprints.
        Only preprints that were not yet posted are processed.
        Only preprints that were ultimately published in the provided list of journals are kept.
        This is useful since the bioRxiv allows only to select by publisher, which may publish many journals.

        Arguments:
            preprints (List[Preprints]): list of preprints to process.
            journals (List): the name of the journals of interest.
        """

        N = len(preprints)
        not_generated = []
        posts = []
        for i, prepr in enumerate(preprints):
            progress(i, N, f"{prepr.biorxiv_doi}          ")
            pre_existing = exists(self.groupid, prepr.biorxiv_doi)
            if not pre_existing and pre_existing is not None:
                paper_doi = prepr.published_doi
                paper = PublishedWithRPF()
                paper.from_doi(paper_doi)
                if paper.rpf and paper.journal in journals:
                    prepr.biorxiv_url = resolve(prepr.biorxiv_doi)  # relies of slow webservice, so we do it only when necessary
                    hypo_post = HypoPostRPF()
                    hypo_post.generate(prepr, paper, embo_press_template)
                    target = Target(prepr.biorxiv_url, prepr.biorxiv_doi, prepr.preprint_title)
                    posts.append({'annotation': hypo_post, 'target': target})
                else:
                    not_generated.append({'doi': prepr.biorxiv_doi, 'reason': f"{'rpf issue' if not paper.rpf else ''} {'not in journals' if not paper.journal in journals else ''}"})
            else:
                not_generated.append({'doi': prepr.biorxiv_doi, 'reason': f'pre_existing={pre_existing}'})
        if not_generated:
            print(f"{len(not_generated)} records were NOT generated:")
            pprint(not_generated)
        return posts

    def post(self, groupid: str, posts:  List[Dict[HypoPostRPF, Target]]) -> int:
        """
        Posts the posts (!) on hypothesis in the specified group.

        Arguments:
            groupid (str): id of the group where the posts should be posted
            postss (List[Dict[HypoPostRPF, Target]]): the list of annotations with their targets
        """

        permissions = HYPO.helpers.permissions(
            read=[f'group:{groupid}'],
            update=[f'acct:{HYPOTHESIS_USER}@hypothes.is'],
            delete=[f'acct:{HYPOTHESIS_USER}@hypothes.is'],
            admin=[f'acct:{HYPOTHESIS_USER}@hypothes.is']
        )
        posted = 0
        N = len(posts)
        for i, post in enumerate(posts):
            annotation = post['annotation']
            target = post['target']
            progress(i, N, f"{target.doi}           ")
            response = post_one(permissions, groupid, target, annotation)
            if response.status_code == 200:
                hyp_id = response.json()['id']
                posted += 1
            else:
                hyp_id = ''
                print(response.text)
            time.sleep(0.1)
        return posted

    def post_all(self, prefixes: List[str], journals: List[str], start_date: str, end_date: str):
        """
        Retrieves preprints that were published in the specified journals and published during a specific interval of time.
        Posts templated annotations linking to the Review Process Files of the published paper.

        Arguments:
            group_name (str): the name of the hypothes.is group where annotations will be posted.
            prefixes (List): the list of publishers doi prefixes.
            journals (List): the list of the selected journals.
            start_date (str): the start date of the time interval (format YYYY-MM-DD).
            end_date (str): the end date of the time interval (format YYYY-MM-DD).
        """

    
        if self.groupid:
            print(f"Retrieving preprints for {', '.join(prefixes)} from bioRxiv.")
            preprints = self.retrieve_preprints(prefixes, start_date, end_date)

            print(f"Genrating posts by resolving dois and generating RPF links.")
            posts = self.generate(preprints, journals)

            print(f"Posting to hypothes.is group {self.groupid}")
            posted = self.post(self.groupid, posts)

            print(f"Posted {posted} records")


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

    Traxiv(group_name).post_all(prefixes, journals, start_date, end_date)

if __name__ == "__main__":
    main()