import matplotlib.pyplot as plt
from igc_analyser import TrackAnalyser
import os
import numpy as np
import logging
import json
import time

logging.basicConfig(level=logging.INFO)

igc_folder = "../data/full/"
flight_data_file = "../data/full/flights.json"
output_file = "../data/full/flights_analysed.json"

def process_single_file(path):
    t = TrackAnalyser(path)
    # find wether baro can be used or not and if we can default to gnss altitude
    for use_baro in (True, False):
        sanity = t.check_track_sanity(use_baro=use_baro)
        if sanity == 0: break
    if sanity != 0:
        if t.check_track_sanity(use_baro=use_baro):
            logging.debug(f"{path} is not safe to extract data from, sanity : {sanity}")
            return None, None
    t.process(use_baro=use_baro)
    ga_filt = [val for pos, val in enumerate(t.glide_angles) if t.glide_mask[pos] == 1]
    return ga_filt, t.track_mean_time_delta

def format_eta(secs):
    hms = [secs//3600, secs%3600//60, secs%3600%60]
    hms = ["0"*int(len(str(i)) == 1) + str(i) for i in hms]
    return ":".join(hms)

def process_folder(flights):
    no_file = -1
    nb_tot_file = len(flights)
    time_start = time.time()
    perc = 0
    eta_hours = 0
    eta_min = 0
    eta_sec = 0
    for flight_id in flights:
        no_file += 1
        if flights[flight_id] is None:
            logging.debug(f"{flight_id} has incomplete data")
            continue
        if not 'gps' in flights[flight_id] or not 'wing' in flights[flight_id]:
            logging.debug(f"{flight_id} has incomplete data")
            continue
        path = os.path.join(igc_folder, flights[flight_id]['gps'])
        ga, mtd = None, None
        try:
            ga, mtd = process_single_file(path)
        except Exception as e:
            logging.debug(e)
            continue
        if ga is None or mtd is None:
            continue
        flights[flight_id]['glide_angles'] = ga
        flights[flight_id]['sampling'] = mtd

        if (no_file%50) == 0:
            perc = (no_file+1)/nb_tot_file
            elapsed_time = time.time() - time_start
            eta = int(elapsed_time / perc * (1 - perc))
            

        print(f"{round(perc*100,1)} % - ETA {format_eta(eta)} - {path}" + " "*30, end="\r")

def yesno(text, default_yes=True):
    choice_text = "[Y/n]" if default_yes else "[y/N]"
    reject_match = ("n", "no") if default_yes else ("y", "yes")
    res = input(f"{text} {choice_text} ")
    return res.lower() not in reject_match

def main():
    with open(flight_data_file, "r") as f:
        flights = json.load(f)
    try:
        process_folder(flights)
    except KeyboardInterrupt:
        print()
        if yesno("Aborted. Save anyway?"):
            if os.path.isfile(output_file):
                if yesno("This file already exists. Override?", default_yes=False):
                    with open(output_file, "w") as f:
                        json.dump(flights, f)
    with open(output_file, "w") as f:
        json.dump(flights, f)

if __name__ == "__main__":
    main()