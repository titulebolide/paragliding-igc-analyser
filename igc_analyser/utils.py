import math
import os


def ga2gr(ga):
    if ga == 0:
        return 1000000
    return -1 / math.tan(ga / 180 * math.pi)


def gr2ga(gr):
    return math.atan(-1 / gr) / math.pi * 180


def yesno(text, default_yes=True):
    choice_text = "[Y/n]" if default_yes else "[y/N]"
    match = ("n", "no") if default_yes else ("y", "yes")
    res = input(f"{text} {choice_text} ")
    return default_yes if (res.lower() not in match) else not default_yes


def get_track_save_dir(workdir, batch_no):
    return os.path.join(workdir, "igcfiles", str(batch_no))


def get_flight_json_file(workdir):
    return os.path.join(workdir, "flight_data.json")


def get_stat_file(workdir):
    return os.path.join(workdir, "flight_stat.dat")


def get_json_file_path_from_igc(workdir, igcfile):
    flight_data_file = igcfile.replace(".igc", ".json")
    flight_data_path = os.path.join(workdir, "igcfiles", flight_data_file)
    return flight_data_path
