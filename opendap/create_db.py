
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Catalog, File

# # create engine and make tables
# engine = create_engine(DATABASE_URL, echo=False)
# #Base.metadata.create_all(engine)
#
# # create session
# Session = sessionmaker(bind=engine)
# session = Session()

# datetime.strptime(
#     ds.time_coverage_end, '%Y-%m-%dP%H:%M:%S')
#session.commit()

#session.add_all(measurements)
#session.commit()
