import os
from dotenv import load_dotenv
from hypothepy.v1.api import HypoApi

load_dotenv(dotenv_path='./.env')
HYPOTHESIS_USER=os.getenv("HYPOTHESIS_USER")
HYPOTHESIS_API_KEY=os.getenv("HYPOTHESIS_API_KEY")
HYPO = HypoApi(HYPOTHESIS_API_KEY, HYPOTHESIS_USER)
