import os
from pymongo import MongoClient
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
from pymongo.cursor import Cursor
from typing import Dict, Tuple
from dotenv import load_dotenv
from .toolbox import Preprint, Published, HypoPost

load_dotenv(dotenv_path='./.env')
USER = os.getenv("DATABASE_USER")
PASSWORD = os.getenv("DATABASE_PASSWORD")

class MongoPreprints:
    """
    Handles the transactinos with MongoDB Atlas database. It is used to keep track of what has aleady been posted or not without having to bombard the hypothe.is API.
    
    Arguments:
        db_name (str): the name of the database
    """

    def __init__(self, db_name: str):
        self.client = MongoClient(f"mongodb+srv://{USER}:{PASSWORD}@cluster0-ifnre.mongodb.net/test?retryWrites=true&w=majority")
        self.db = self.client[db_name]
        self.group = None

    def collection(self, groupid: str) -> str:
        """
        Creates and sets the handle to the MongoDB collection that represents the specified hypothes.is group.

        Arguments:
            groupid (str): the unique id of the hypothes.is group

        Returns:
            str: the groupid
        """
        self.group = self.db[groupid]

    def insert(self, preprint: Preprint, paper: Published, hypo_post: HypoPost) -> InsertOneResult:
        """
        Inserts a new document to store information about the linked preprint, published paper and prepared hypothes.is post.

        Arguments:
            preprint (Preprint): the preprint metadata from bioRxiv.
            paper (Published): the paper linked to the preprint.
            hypo_post (HypoPost): the hypothes.is post
        
        Returns:
           str: the MongoDB response
        """
        if not self.exists(preprint.biorxiv_doi):
            return self.group.insert_one({'preprint': preprint.to_dict(), 'paper': paper.to_dict(), 'annotation':hypo_post.to_dict()})
        else:
            return None

    def exists(self, doi: str) -> bool:
        """
        Checks whether a document corresonding to a given preprint already exists in the database.

        Arguments:
           doi (str): the doi of the **preprint**.

        Returns:
           bool: True if already in database
        """

        return self.find_one(doi) is not None

    def find_one(self, doi: str) -> Dict:
        """
        Finds one document in the database that corresponds to the preprint specified by its doi.

        Arguments:
            doi (str): the doi of the **preprint**.

        Returns:
            dict: the document retrieved from the database.
        """
        return self.group.find_one({'preprint.biorxiv_doi': doi})

    def not_yet_posted(self) -> Tuple[Cursor, int]:
        """
        Retrieves the documents for posts that are not yet live on hypothes.is and thefore that do not yet have a hypothes.is id.

        Returns:
           Tuple[Cursor, int]: a Tuple with the results returned by the databse and the number of documents.
        """

        query = {'annotation.hypothesis_id': {'$eq': ''}}
        results = self.group.find(query)
        N = self.group.count(query) # len(results) would not work since object of type 'Cursor' has no len()
        return results, N

    def update(self, doi: str, hyp_id: str) -> UpdateResult:
        """
        Updates a document to add its hypothes.is id once it is posted and live.

        Arguments:
            doi (str): the doi of the **preprint**.
            hyp_id (str): the hypothes.is id assigned to the post.
        """

        return self.group.update_one(
            {'preprint.biorxiv_doi': doi},
            {'$set':
                {'annotation.hypothesis_id': hyp_id}
            }
        )

    def delete_one(self, hyp_id) -> DeleteResult:
        """
        Deletes a single document corresonding to the specified hypothes.is post.

        Arguments:
            hyp_id (str): the hypothes.is id of the post that needs to be deleted.
        
        Returns:
            DeleteResults: the response of the database
        """

        return self.group.delete_one({'annotation.hypothesis_id': hyp_id})

    def drop(self):
        """
        Drops the MongoDB collection corresponding to the hypothes.is group.
        """

        self.db.drop_collection(self.group)
        self.group = None

    def count(self) -> int:
        """
        Returns the number of documents stored in the colection correspondin to the hypothes.is group.
        """

        return self.group.count_documents({})

