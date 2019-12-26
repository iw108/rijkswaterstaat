
from datetime import datetime

from waterinfo.public import Waterhoogte


waterhoogte = Waterhoogte()
station = waterhoogte.stations[0]

start_date = datetime(2019, 2, 1)
end_date = datetime(2019, 2, 3)

data_between_dates = waterhoogte.get_data_between_dates(
    station['name'], start_date, end_date, parse=True
)

data_from_horizon = waterhoogte.get_data_from_horizon(
    station['name'], start_date, end_date
)

waterhoogte.update_station_crs('epsg:4326')
print(data_from_horizon)
