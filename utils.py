import math

def ga2gr(ga):
    if ga == 0:
        return 1000000
    return -1/math.tan(ga/180*math.pi)

def gr2ga(gr):
    return math.atan(-1/gr)/math.pi*180

def yesno(text, default_yes=True):
    choice_text = "[Y/n]" if default_yes else "[y/N]"
    match = ("n", "no") if default_yes else ("y", "yes")
    res = input(f"{text} {choice_text} ")
    return default_yes if (res.lower() not in match) else not default_yes
