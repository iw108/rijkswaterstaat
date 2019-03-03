
from datetime import datetime
import json
import logging.config
import os


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base, Catalog, File
from ..settings import CATALOG_URL, DATA_URL, DATA_DIR, DATABASE_URL, DATABASE_PATH, LOG_DEFAULT


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
        except:
            session.rollback()
        finally:
            session.close()
