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

logging.basicConfig(level=logging.DEBUG)


def process_single_file(path):
    t = TrackAnalyser(path)
    # find wether baro can be used or not and if we can default to gnss altitude
    for use_baro in (True, False):
        sanity = t.check_track_sanity(use_baro=use_baro)
        if sanity == 0: break
    if sanity != 0:
        if t.check_track_sanity(use_baro=use_baro):
            logging.debug(f"{'/'.join(path.split('/')[-2:])} is not safe to extract data from, sanity : {sanity}")
            return None, None
    t.process(use_baro=use_baro)
    ga_filt = [val for pos, val in enumerate(t.glide_angles) if t.glide_mask[pos] == 1]
    outfile = path.replace(".igc", ".json")
    with open(outfile, "w") as f:
        json.dump({
            "glide_angles": ga_filt,
            "sampling": t.track_mean_time_delta,
        }, f)

def format_eta(secs):
    hms = [secs//3600, secs%3600//60, secs%3600%60]
    hms = ["0"*int(len(str(i)) == 1) + str(i) for i in hms]
    return ":".join(hms)

def process_folder(igc_indir, flights):
    no_file = -1
    nb_tot_file = len(flights)
    time_start = time.time()
    perc = 0
    for flight_id in flights:
        no_file += 1
        if flights[flight_id] is None:
            logging.debug(f"{flight_id} has incomplete data")
            continue
        if not 'gps' in flights[flight_id] or not 'wing' in flights[flight_id]:
            logging.debug(f"{flight_id} has incomplete data")
            continue
        path = os.path.join(igc_indir, flights[flight_id]['gps'])
        try:
            process_single_file(path)
        except Exception as e:
            logging.debug(e)
            continue

        if (no_file%50) == 0:
            perc = (no_file+1)/nb_tot_file
            elapsed_time = time.time() - time_start
            eta = int(elapsed_time / perc * (1 - perc))
        print(f"{round(perc*100,1)} % - ETA {format_eta(eta)} - {flights[flight_id]['gps']}" + " "*30, end="\r")

def main(igc_indir, flight_infile):
    with open(flight_infile, "r") as f:
        flights = json.load(f)
    flights = process_folder(igc_indir, flights)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workdir", type=str, help="Work directory")
    args = parser.parse_args()

    workdir = os.path.abspath(args.workdir)
    igc_indir = os.path.join(workdir, "igcfiles")
    flight_infile = utils.get_flight_json_file(workdir)

    if not os.path.exists(igc_indir) or not os.path.isfile(flight_infile):
        print("The input directory is invalid. Exiting.")
        exit(1)

    main(igc_indir, flight_infile)