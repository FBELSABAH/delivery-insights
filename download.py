from pathlib import Path
from urllib.request import urlopen
import hashlib
ROOT=Path(__file__).resolve().parent
EXPECTED='967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784'
if __name__ == '__main__':
    p=ROOT/'data';p.mkdir(exist_ok=True)
    with urlopen('https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce',timeout=120) as response:
        content=response.read()
    if hashlib.sha256(content).hexdigest()!=EXPECTED:
        raise SystemExit('Source archive changed. Review the new version before updating the pinned checksum.')
    (p/'olist.zip').write_bytes(content)
    print('Downloaded and verified source archive.')
