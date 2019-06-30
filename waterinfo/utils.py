
import pyproj


class Projection(object):
    """
    class to transform between two coordinate systems
    """

    def __init__(self, first_projection, second_projection):
        self.first_projection = pyproj.Proj(init=first_projection)
        self.second_projection = pyproj.Proj(init=second_projection)

    def forwards(self, lon, lat):
        """
        transform longitude and latitude from first to second coord system
        """
        return pyproj.transform(
            self.second_projection, self.first_projection, lon, lat
        )

    def backwards(self, lon, lat):
        """
        transform longitude and latitude from second to first coord system
        """
        return pyproj.transform(
            self.second_projection, self.first_projection, lon, lat
        )
