
from datetime import datetime
import json
import logging
import logging.config
import os
import re

from bs4 import BeautifulSoup
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, Catalog, File
from .settings import (
    CATALOG_URL, DATA_DIR, DATA_URL, DATABASE_URL, DATABASE_PATH, LOG_DEFAULT
)
from .utils import OpendapFile


def _get_files(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    files = []
    for item in soup.find_all('a'):
        conditions = (
            re.match(
                r'(^catalog.html)|(.*catalog.html)$', item.attrs.get('href')
            ),
            re.match(r'(^\d{2})|(^id\d+)', item.text)
        )

        if all(conditions):
            files.append(item.text.strip('/'))
    return files


def extract_data():
    # step 1: get catalogs
    logging.config.dictConfig(LOG_DEFAULT)
    logging.info('Getting catalogs.')
    try:
        catalog_list = _get_files(os.path.join(CATALOG_URL, 'catalog.html'))
    except Exception:
        logging.error("Could not get catalog files")
        raise
    logging.info(f"Getting catalog files. ({len(catalog_list)} catalogs)")

    # step 2: process catalogs and get catalog files
    catalogs = []
    for index, file in enumerate(catalog_list):
        catalog = {
          'pk': int(re.findall(r'(^\d+)', file)[0]),
          'full_name': re.findall(r'^\d+_(.*)', file)[0]
        }

        full_url = (
            f"{CATALOG_URL}/{catalog['pk']:02d}_{catalog['full_name']}/"
            "nc/catalog.html"
        )

        try:
            catalog.update({'files': _get_files(full_url)})
        except Exception:
            logging.error("Failed to get files for catalog no. {index + 1}")
            raise

        if catalog['files']:
            catalog.update({
                'id': int(re.findall(r'^id(\d+)-', catalog['files'][0])[0])
            })
            catalogs.append(catalog)

    number_of_files = sum([len(catalog['files']) for catalog in catalogs])
    logging.info(f"{number_of_files} catalog files")

    # step 3: read the files and extract the meta info
    all_files = []
    for index, catalog in enumerate(catalogs):
        files = catalog.pop('files')
        logging.info(f"Processing {catalog['full_name']}.")

        count = 0
        for file in files:
            file_url = (
                f"{DATA_URL}/{catalog['pk']:02d}_{catalog['full_name']}"
                "/nc/{file}"
            )
            try:
                meta = OpendapFile(file_url).meta
                meta.update(catalog_id=catalog['id'])
                all_files.append(meta)
                count += 1
            except Exception as e:
                logging.warning(f"Skipping file {file_url}. Error {e}")

        logging.info(
            (f"Finished with {catalog['full_name']}"
             f" ({index + 1}/{len(catalogs)})."
             f"Extracted information from {count}/{len(files)} files")
        )

        catalogs[index] = catalog

    with open(os.path.join(DATA_DIR, 'catalogs.json'), 'w') as file:
        json.dump(catalogs, file, indent=4)

    with open(os.path.join(DATA_DIR, 'files.json'), 'w') as file:
        json.dump(all_files, file, indent=4)


def create_db():

    if not os.path.exists(DATABASE_PATH):
        # add tables to database
        engine = create_engine(DATABASE_URL, echo=False)
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        # get catalogs
        catalog_path = os.path.join(DATA_DIR, 'catalogs.json')
        if os.path.exists(catalog_path):
            with open(catalog_path, 'r') as file:
                catalogs = json.load(file)
                for index, catalog in enumerate(catalogs):
                    catalogs[index] = Catalog(**catalog)

        # get files
        file_path = os.path.join(DATA_DIR, 'files.json')
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                files = json.load(file)
                for index, file in enumerate(files):
                    for key in ('time_coverage_start', 'time_coverage_end'):
                        file[key] = datetime.strptime(
                            file[key], '%Y-%m-%dP%H:%M:%S')
                    files[index] = File(**file)

        try:
            logging.config.dictConfig(LOG_DEFAULT)
            session.add_all(catalogs + files)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
