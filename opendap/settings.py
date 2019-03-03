import os

# urls for open dap
DATA_URL = ('http://opendap.deltares.nl/thredds/'
            'dodsC/opendap/rijkswaterstaat/waterbase')

CATALOG_URL = ('http://opendap.deltares.nl/thredds/'
               'catalog/opendap/rijkswaterstaat/waterbase')


# default timezone measurements are assumed to be in
TIMEZONE = "MET"

# set up paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# database info
DATABASE_PATH = os.path.join(DATA_DIR, 'opendap.db')
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'


# set up logging defaults
LOG_DEFAULT = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'file_handler': {
            'level': 'INFO',
            'filename': os.path.join(LOG_DIR, 'opendap.log'),
            'class': 'logging.FileHandler',
            'formatter': 'standard'
        }
    },
    'loggers': {
        '': {
            'handlers': ['file_handler'],
            'level': 'INFO',
            'propagate': True
        },
        'sqlalchemy.engine': {
            'handlers': ['file_handler'],
            'level': 'INFO',
            'propagate': True
        },
    }
}
