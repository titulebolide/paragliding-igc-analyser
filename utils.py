import math

def ga2gr(ga):
    if ga == 0:
        return 1000000
    return -1/math.tan(ga/180*math.pi)

def gr2ga(gr):
    return math.atan(-1/gr)/math.pi*180