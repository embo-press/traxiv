"""
A set of classes and functions used to manipulate bioRxiv preprints, published papers and hypothes.is posts.
"""

from typing import List, Dict
from . import HYPO
from hypothepy.v1.helpers import PermissionsHelper
from .utils import info


class AsDict:
    """
    Serialize itself recursively to a dictionary with all the attributes.
    It is practical when posting simple objects to MongoDB.
    """

    def to_dict(self) -> Dict:
        """
        Returns a dictionary with the attribute names as keys and attribute value as values. If a value is itself an object, it is first recursively serialized to a dictionary.
        """
        d = {}
        for k, v in self.__dict__.items():
           d[k] = v.to_dict() if isinstance(v, AsDict) else v
        return d

class Preprint(AsDict):
    """
    Captures all the metadata elements returned by the bioRxiv API for a given preprint.

    Attributes:
        biorxiv_doi (str): the doi of the preprint
        published_doi (str): the doi of the associated published paper
        preprint_title (str): the title of the preprint
        preprint_category (str): the subject category to which bioRxiv assigned the preprint
        preprint_date (str): the date of posting (in format YYYY-MM-DD)
        published_date (str): the date of publication (in format YYYY-MM-DD) of the associated paper
        published_citation_count: the number of citations; unclear whether it is to the paper or preprint and what is the source of the data
    """

    def __init__(self,
        biorxiv_doi='',
        biorxiv_url='',
        published_doi='',
        preprint_title='',
        preprint_category='',
        preprint_date='',
        published_date='',
        published_citation_count=''
    ):
        self.biorxiv_doi = biorxiv_doi
        self.biorxiv_url = biorxiv_url
        self.published_doi = published_doi
        self.preprint_title = preprint_title
        self.preprint_category = preprint_category
        self.preprint_date = preprint_date
        self.published_date = published_date
        self.published_citation_count = published_citation_count


class Published(AsDict):
    """
    Simple representation of essential metadata about a published paper.

    Arguments:
        doi (str): the DOI of the paper.
        journal (str): the name of the journal in which the paper was published.
        subject (List): the list of subject areas assigned by CrossRef to the journal.
    """

    def __init__(self, doi: str='', journal: str='', subject: List=[]):
        self.doi = doi
        self.journal = journal
        self.subject = subject

    def from_doi(self, doi: str):
        """
        Populates the metadata fields for a paper identified with its DOI.
        The metadata is retrieved from CrossRef.

        Arguments:
            doi (str): the DOI of the paper.
        """

        self.doi: str = doi
        crossref_metadata = info(self.doi)
        self.journal: str = crossref_metadata['container-title']
        self.subject: List = []
        if 'subject' in crossref_metadata:
            self.subject = crossref_metadata['subject'] # seems to be the broad subject of the _journal_ where the paper was published

class HypoPost(AsDict):
    """
    A hypothes.is post.

    Arguments:
        annotation_text (str): the markdown text that will be posted on hypothe.is
        tags (List): the list of tags that will aggregate the post with similarly tagged posts on hypothes.is
        hypothesis_id (str): the unique id assigned by hypothes.is when the post is put online.
    """

    def __init__(self, annotation_text: str='', hypothesis_id: str='', tags: List=[]):
        self.annotation_text = annotation_text
        self.tags = tags
        self.hypothesis_id = hypothesis_id


class Target:
    """
    The target to which a hypothes.is post should be linked to.

    Arguments:
        url (str): the url of the target page to which the hypothes.is post should be linked to.
        doi (str): the doi of the tarrget preprint.
        title (str): the title of the target page
    """
    def __init__(self, url:str, doi: str, title:str):
        self.url = url
        self.doi = doi
        self.title = title

def post_one(permissions:PermissionsHelper, groupid:str, target:Target, post:HypoPost) -> Dict:
    """
    Posts a HypoPost linked to a specific Target to a specific hypothes.is group.
    Note that post_one() uses HYPO, an instance of hypothepy.v1.api.HypoApi that has been initialized with the crendentials of the user.

    Usage:
        from . import HYPOTHESIS_USER
        from .utils import get_groupid
        groupid = get_groupid('test')
        perms = HYPO.helpers.permissions(
            read=[f'group:{groupid}'],
            update=[f'acct:{HYPOTHESIS_USER}@hypothes.is'],
            delete=[f'acct:{HYPOTHESIS_USER}@hypothes.is'],
            admin=[f'acct:{HYPOTHESIS_USER}@hypothes.is']
        )
        target = Target("http://mysite.com/target_page", "Title of the target page")
        post = HypoPost(text="blahblah", tags=['testpost'])
        response = post_one(perms, groupid, target, post)
        if response.status_code == 200:
            print("success!")

    Arguments:
        permissions (PermissionsHelper): the set of permissions with which the post will be posted on hypothes.is
        groupid (str): the idenfier of the group to which this post will be posted.
        target (Target): the target page to which the post should be linked to (includes url and title).
        post (HypoPost): the post itself, with the markdown text and tags.

    Returns:
        The response from the hypothes.is REST API to the request.
    """
    highwire = HYPO.helpers.highwire(doi=[target.doi])
    document = HYPO.helpers.documents(title=target.title, highwire=highwire)
    response = HYPO.annotations.create(
        target.url,
        permissions=permissions,
        text=post.annotation_text,
        tags=post.tags,
        document=document,
        group=groupid
    )
    return response
