import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from hypothepy.v1.api import HypoApi

load_dotenv(dotenv_path='./.env')
HYPOTHESIS_USER=os.getenv("HYPOTHESIS_USER")
HYPOTHESIS_API_KEY=os.getenv("HYPOTHESIS_API_KEY")
HYPO = HypoApi(HYPOTHESIS_API_KEY, HYPOTHESIS_USER)


logger = logging.getLogger('traxiv logger')
logger.setLevel(logging.INFO)
log_dir = Path('./log')
log_file = Path('traxiv.log')
if not log_dir.exists():
    log_dir.mkdir()
log_path = log_dir / log_file
fh = logging.FileHandler(log_path)
fh.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)
logger.addHandler(fh)
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(formatter)
logger.addHandler(sh)
