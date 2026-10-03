"""Site frames and shared levels (all heights in metres relative to the obelisk base = world z 0)."""
import math
import numpy as np

DOME_XY = (-321.5, -8.7)                       # crossing / dome axis (OSM parts)
AXIS_ANG = math.atan2(-DOME_XY[1], -DOME_XY[0])  # basilica axis bearing toward the obelisk (rad, from +x)
FLOOR = 6.0                                    # basilica / portico floor
PIAZZA_AT_STEPS = 1.0                          # piazza level at the foot of the steps

# basilica local frame: u along the axis toward the facade (east), v to the north, origin = dome axis on the floor
def B2W(u, v, z=0.0):
    c, s = math.cos(AXIS_ANG), math.sin(AXIS_ANG)
    return (DOME_XY[0] + u * c - v * s, DOME_XY[1] + u * s + v * c, z)

def W2B(x, y):
    c, s = math.cos(AXIS_ANG), math.sin(AXIS_ANG)
    dx, dy = x - DOME_XY[0], y - DOME_XY[1]
    return (dx * c + dy * s, -dx * s + dy * c)

def basilica_matrix():
    c, s = math.cos(AXIS_ANG), math.sin(AXIS_ANG)
    M = np.eye(4)
    M[:3, 0] = (c, s, 0); M[:3, 1] = (-s, c, 0); M[:3, 2] = (0, 0, 1); M[:3, 3] = (DOME_XY[0], DOME_XY[1], FLOOR)
    return M
