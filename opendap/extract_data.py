
import json
import logging, logging.config
import os
import re
import requests

from bs4 import BeautifulSoup

from settings import LOG_DEFAULT, DATABASE_URL, CATALOG_URL, DATA_URL, DATA_DIR
from utils import OpendapFile


def get_files(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    files = []
    for item in soup.find_all('a'):
        if (re.match('(^catalog.html)|(.*catalog.html)$', item.attrs.get('href'))
                and re.match('(^\d{2})|(^id\d+)', item.text)):
            files.append(item.text.strip('/'))
    return files


# configure logging
logging.config.dictConfig(LOG_DEFAULT)


# get catalogs
logging.info('Getting catalogs.')
try:
    catalog_list = get_files(os.path.j oin(CATALOG_URL, 'catalog.html'))
except:
    logging.error("Could not get catalog files")
    raise

# process catalogs and get catalog files
logging.info(f"Getting catalog files. ({len(catalog_list)} catalogs)")
catalogs = []
for index, file in enumerate(catalog_list):
    catalog = {
      'pk': int(re.findall('(^\d+)', file)[0]),
      'full_name': re.findall('^\d+_(.*)', file)[0]
    }

    full_url = f"{CATALOG_URL}/{catalog['pk']:02d}_{catalog['full_name']}/nc/catalog.html"
    try:
        catalog.update({'files': get_files(full_url)})
    except:
        logging.error("Failed to get files for catalog no. {index + 1}")
        raise

    if catalog['files']:
        catalog.update({'id': re.findall('^id(\d+)-', catalog['files'][0])[0]})
        catalogs.append(catalog)
    else:
        logging.warning(f"No catalog files found for {full_url}")

number_of_files = sum([len(catalog['files']) for catalog in catalogs])
logging.info(f"Finished getting catalog files. {number_of_files} files")

# read the files and extract the meta info
logging.info("Extracting file meta data")
all_files = []
for index, catalog in enumerate(catalogs):
    files = catalog.pop('files')
    logging.info(f"Processing {catalog['full_name']}.")

    count = 0
    for file in files:
        file_url = f"{DATA_URL}/{catalog['pk']:02d}_{catalog['full_name']}/nc/{file}"
        try:
            meta = OpendapFile(file_url).meta
            meta.update(catalog_id=catalog['id'])
            all_files.append(meta)
            count += 1
        except Exception as e:
            logging.warning(f"Skipping file {file_url}. Error {e}")

    logging.info((f"Finished with {catalog['full_name']} ({index + 1}/{len(catalogs)})."
                  f"Extracted information from {count}/{len(files)} files"))

    catalogs[index] = catalog


with open(os.path.join(DATA_DIR, 'catalogs.json'), 'w') as file:
    json.dump(catalogs, file, indent=4)

with open(os.path.join(DATA_DIR, 'files.json'), 'w') as file:
    json.dump(all_files, file, indent=4)





