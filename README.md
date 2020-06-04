# Traxiv

TraXiv is a simple demonstration of the use of the [bioRxiv](https://biorxiv.org) and [hypothes.is](https://web.hypothes.is) APIs to link preprints to the complete peer-review process obtained by [EMBO Press](https://embopress.org).

The posted links can be seen in hypothe.is next to preprints that were published in EMBO Press journals. These posts are aggregated on hypothes.is in the [EMBO Press publisher group](https://hypothes.is/groups/jKiXiKya/embo-press).

## Intro

Traxiv identifies EMBO Press papers for which there is a preprint on bioRxiv. It then generates the links to the respective Review Process Files (RPF) hosted by the journals. The links are then inserted in a template to be posted on hypothes.is and linked to the respective preprints.

It illustrates the use of:
 
- bioRxiv REST API for publishers: https://api.biorxiv.org/publisher
- the python binding to the hypothe.is API: https://github.com/embo-press/hypothepy
- crossref metadata: https://doi.org

## Getting started

Install and activate the python virtual environment:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Credentials to your hypothes.is account should be stored in an `.env` file by editing the provided `.env.example` file. 

**⚠️ Do NOT add, commit or push your `.env` file since it contains your private personal credentials.**

## Examples


### Example 1

Fetching preprints associated with a publisher identified by its **doi prefix**:

```
# embo press is identified by its doi prefix 10.15252
$ python -m src.biorxiv 10.15252 --start 2019-08-01 --end 2019-09-01
# Returns: 
#
# bioRxiv request: https://api.biorxiv.org/publisher/10.15252/2019-08-01/2019-09-01/0
# biorxiv_doi     published_doi   category
# 10.1101/605725 10.15252/embj.2019102870 molecular biology
# 10.1101/528380 10.15252/embj.2019101704 cell biology
```

### Example 2

Posting a simple annotation and deleting it using the `toolbox` module. To run this demonstartion, you have to have a hypothes.is account and have included your hypothes.is username and api_key (see how to obtain an hypothes.is api key at https://web.hypothes.is/developers/) in the `.env` file as shown in `.env.example`.

```
from src import HYPO, HYPOTHESIS_USER # HYPO is an instance of hypothepy.v1.api.HypoApi that has been initialized with the crendentials of the user.
from src.utils import get_groupid # simple utility to retrieve the hyopthe.is groupid from the group name
from src.toolbox import HypoPost, Target, post_one
groupid = get_groupid('test')
print(groupid)
perms = HYPO.helpers.permissions(
    read=[f'group:{groupid}'],
    update=[f'acct:{HYPOTHESIS_USER}@hypothes.is'],
    delete=[f'acct:{HYPOTHESIS_USER}@hypothes.is'],
    admin=[f'acct:{HYPOTHESIS_USER}@hypothes.is']
)
# we want to post the annotation "Great work!" on the target page https://www.embopress.org/journal/17444292
# the annotaiton will have the tag "EMBOpress"
target = Target("https://www.embopress.org/journal/17444292", "Molecular Systems Biology")
post = HypoPost(annotation_text="Great work!", tags=['EMBOpress'])
response = post_one(perms, groupid, target, post)
if response.status_code == 200:
    hyp_id = response.json()['id']
    print(f"posted {hyp_id}")
# checkout https://www.embopress.org/journal/17444292 and open the hypothesis chrome app to see you annotation (after loging in with the same account)
# checkout https://hypothes.is/groups/<groupid>/test
# now we remove the post using its unique identifier hyp_id assigned by hypothes.is upon posting
response = HYPO.annotations.delete(hyp_id)
if response.status_code == 200:
    print(f"deleted {hyp_id}")
# verify that the post has disappeared from https://hypothes.is/groups/<groupid>/test
```

### Example 3

Using a template to generate templated posts.

First, extend the base class `HypoPost` to add a method that generates the text of the annotation with a simple pyhon `string.Template` object.

```
from string import Template
from src.toolbox import HypoPost

class HypoPostTemplated(HypoPost):
    """
    Extends HypoPost to generate a templated annotation.
    """

    def generate(self, msg: str, template: Template):
        """
        Generates the text of the post from a Template.
        
        Arguments:
            msg (str): the specific message to be inserted.
            template (Template): a simple string.Template object to generate the text of the annotation with appropriate substitution
        """

        self.annotation_text = template.substitute({'msg': msg})
        self.tags = ['EMBOPress']
```

Define the template with the appropriate `$msg` substitution variable:

    my_template = Template('**This is a simple demo of templated post.**\n$msg\n---\nIsn\'t it nice?') # this would be normally imported from a file

Create an instance of the HypoPostTemplated object and generate the markdoown text:

    my_post = HypoPostTemplated()
    my_post.generate('### Great work!\n', my_template)
    print(my_post.annotation_text)

Let's post it using the permissions `perms`, `groupid` and `target` from Example 2 above.

    response = post_one(perms, groupid, target, my_post)
    if response.status_code == 200:
        hyp_id = response.json()['id']
        print(f"posted {hyp_id}")

Check the nice post at https://www.embopress.org/journal/17444292 

And purge:

    print(f"deleting {hyp_id}")
    response = HYPO.annotations.delete(hyp_id)
    if response.status_code == 200:
        print(f"deleted {hyp_id}")

### Example 4

Automated posting of templated annotations links to hypothes.is:

```
$ python -m src.traxiv --help
usage: postrpf.py [-h] [--prefixes PREFIXES] [--journals JOURNALS]
                  [--start START] [--end END] [--group GROUP]

Posts RPF files to hypothes.is

optional arguments:
  -h, --help           show this help message and exit
  --prefixes PREFIXES  List of publisher's doi prefixes to retrieve
                       corresponding preprints. (default: ['10.15252',
                       '10.26508'])
  --journals JOURNALS  The journals to scan. (default: ['The EMBO Journal',
                       'EMBO reports', 'EMBO Molecular Medicine', 'Molecular
                       Systems Biology', 'Life Science Alliance'])
  --start START        Start date for the search (format YYYY-MM-DD) (default:
                       2019-01-01)
  --end END            End date for the search (format YYYY-MM-DD) (default:
                       2019-08-25)
  --group GROUP        Name of the hypothesis group (default: )
```

Example:

    python -m src.traxiv --group test --start 2019-08-01 
    python -m src.purge test
