
from datetime import datetime, timedelta

from matplotlib import pyplot as plt

from waterinfo.public import Waterhoogte


waterhoogte = Waterhoogte()
station = waterhoogte.stations[0]

start_date = datetime.now() - timedelta(days=3)
end_date = datetime.now() - timedelta(days=1)


data_from_horizon = waterhoogte.get_data_from_horizon(
    station['name'], start_date, end_date
)
print(data_from_horizon)


data_between_dates = waterhoogte.get_data_between_dates(
    station['name'], start_date, end_date, parse=True
)

plt.figure()
plt.plot(data_between_dates)
plt.ylabel('tidal level (cm)')
plt.xlabel('date')
