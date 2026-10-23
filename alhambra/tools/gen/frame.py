"""Local frame of the demo: metres, x east, z south, from 37.17725 N, 3.5897 W (equirectangular,
the same mapping as tools/prepare_context.py). The plateau of the Alhambra is modelled flat at y = 0,
which corresponds to E0 = 774 m above sea level."""
import os
LAT0, LON0 = 37.17725, -3.5897
KX, KZ = 88700.0, 111320.0
E0 = 774.0
ASSETS = os.environ.get('ALHAMBRA_ASSETS', '/home/kazu/work/alhambra-assets')
PUBLIC = os.path.join(os.path.dirname(__file__), '..', '..', 'public')

def local(lon, lat):
    return (lon - LON0) * KX, (LAT0 - lat) * KZ
