import os

from sqlalchemy import Column, Float, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from settings import CATALOG_URL, DATA_URL


Base = declarative_base()


class Catalog(Base):
    __tablename__ = 'catalogs'

    pk = Column(Integer, primary_key=True)
    id = Column(Integer)
    full_name = Column(String(50))
    files = relationship("File", back_populates="catalog")

    def __repr__(self):
       return f"<catalog {self.full_name}>"

    @property
    def url(self):
        return f"{CATALOG_URL}/{int(self.pk):02d}_{self.full_name}/nc/catalog.html"


class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    station_name = Column(String(50), nullable=False)
    location_code = Column(String(50), nullable=False)
    epsg = Column(Integer, default=4236)
    lat = Column(Float)
    lon = Column(Float)
    time_coverage_start = Column(DateTime)
    time_coverage_end = Column(DateTime)

    # relationships
    catalog_id = Column(Integer, ForeignKey('catalog.id'))
    catalog = relationship("Catalog", back_populates="files")

    def __repr__(self):
        return f"<File {self.station_name} - {self.catalog.full_name}>"

    @property
    def url(self):
        return (f"{DATA_URL}/{self.catalog.pk:02d}_{self.catalog.full_name}/"
                f"nc/id{self.catalog.id}-{self.location_code.upper()}.nc")
