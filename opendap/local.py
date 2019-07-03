
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

from .models import Base, Catalog as CatalogModel, File as FileModel
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


class Catalog(object):

    def __init__(self, filename):
        self.id = None
        self.filename = filename

    def get_pk(self):
        return int(re.findall(r'(^\d+)', self.filename)[0])

    def get_fullname(self):
        return re.findall(r'^\d+_(.*)', self.filename)[0]

    def get_data_url(self):
        return f"{DATA_URL}/{self.filename}/nc/"

    def get_catalog_url(self):
        return f"{CATALOG_URL}/{self.filename}/nc/catalog.html"

    @property
    def as_json(self):
        return {
            'pk': self.get_pk(),
            'full_name': self.get_fullname(),
            'id': self.id
        }

    def get_files(self):
        files = _get_files(self.get_catalog_url())
        self.id = int(re.findall(r'^id(\d+)-', files[0])[0])
        return files

    def __repr__(self):
        return f"{self.filename}"


def get_catalogs():
    catalogs = _get_files(os.path.join(CATALOG_URL, 'catalog.html'))
    return [Catalog(catalog) for catalog in catalogs]


def extract_data():

    logging.config.dictConfig(LOG_DEFAULT)

    catalogs = get_catalogs()
    cat_count = len(catalogs)

    all_catalogs, all_files = [], []
    for cat_no, catalog in enumerate(catalogs):
        logging.info(
            f"Processing {cat_no + 1}/{cat_count}: {catalog.filename}"
        )
        try:
            catalog_files = catalog.get_files()
        except Exception as e:
            logging.error("Failed to get files")
            raise e

        logging.info(f"Catalog {cat_no + 1}: {len(catalog_files)} files")
        for file in catalog_files:
            file_url = os.path.join(catalog.get_data_url(), file)
            try:
                meta = OpendapFile(file_url).meta
                meta.update(catalog_id=catalog.id)
                all_files.append(meta)
            except Exception as e:
                logging.warning(f"Skipping file {file_url}. Error {e}")

        all_catalogs.append(catalog.as_json)

    # now save
    with open(os.path.join(DATA_DIR, 'catalogs.json'), 'w') as file:
        json.dump(all_catalogs, file, indent=4)

    with open(os.path.join(DATA_DIR, 'files.json'), 'w') as file:
        json.dump(all_files, file, indent=4)


def create_db():

    if os.path.exists(DATABASE_PATH):
        raise ValueError("Database already exists")

    catalog_path = os.path.join(DATA_DIR, 'catalogs.json')
    file_path = os.path.join(DATA_DIR, 'files.json')
    if not (os.path.exists(catalog_path) and os.path.exists(catalog_path)):
        raise ValueError('Please ensure files exists')

    # add tables to database
    engine = create_engine(DATABASE_URL, echo=False)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    with open(catalog_path, 'r') as file:
        catalogs = json.load(file)
        for index, catalog in enumerate(catalogs):
            catalogs[index] = CatalogModel(**catalog)

    with open(file_path, 'r') as file:
        files = json.load(file)
        for index, file in enumerate(files):
            for key in ('time_coverage_start', 'time_coverage_end'):
                file[key] = datetime.strptime(
                    file[key], '%Y-%m-%dP%H:%M:%S'
                )
            files[index] = FileModel(**file)

    try:
        logging.config.dictConfig(LOG_DEFAULT)
        session.add_all(catalogs + files)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
