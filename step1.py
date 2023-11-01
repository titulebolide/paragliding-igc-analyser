"""
Analyses the raw flight data in order to extract 
the glide angle throughout the flight
"""

from igc_analyser import TrackAnalyser
import os
import logging
import json
import time
import argparse
import utils

logging.basicConfig(level=logging.INFO)


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

def process_folder(igc_indir, flights):
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
        path = os.path.join(igc_indir, flights[flight_id]['gps'])
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

def main(igc_indir, flight_infile, outfile):
    with open(flight_infile, "r") as f:
        flights = json.load(f)
    try:
        process_folder(igc_indir, flights)
    except KeyboardInterrupt:
        if not utils.yesno("Aborted. Save anyway?"):
            return
    with open(outfile, "w") as f:
        json.dump(flights, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("indir", type=str, help="Work directory")
    args = parser.parse_args()

    indir = os.path.abspath(args.indir)
    igc_indir = os.path.join(indir, "igcfiles")
    flight_infile = os.path.join(indir, "flight_data.json")
    outfile = os.path.join(args.indir, "flights_analysed.json")

    if not os.path.exists(igc_indir) or not os.path.isfile(flight_infile):
        print("The input directory is invalid. Exiting.")
        exit(1)

    if os.path.exists(outfile):
        if not utils.yesno("This file already exists. Override?", default_yes=False):
            print("Exiting.")
            exit(0)

    if not os.path.isdir(os.path.dirname(outfile)):
        print(f"{os.path.dirname(outfile)} is not a valid directory. Exiting.")
        exit(1)

    if not outfile.endswith(".json"):
        print("The output file must ends with the json extension. Exiting.")
        exit(1)

    main(igc_indir, flight_infile, outfile)