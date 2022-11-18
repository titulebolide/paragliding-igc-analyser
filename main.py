import matplotlib.pyplot as plt
from igc_analyser import TrackAnalyser
import os 
import numpy as np
import logging
import time

logging.basicConfig(level=logging.INFO)

igc_folder = "../data/full/"

with open("flight_data.json", "r") as f:
    fligths = json.load(f)

def main():
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
        if (no_file%50) == 0:
            perc = (no_file+1)/nb_tot_file
            elapsed_time = time.time() - time_start
            eta = int(elapsed_time / perc * (1 - perc))
            eta_hour = eta//3600
            eta_min = eta%3600//60
            eta_sec = eta%3600%60
        print(f"{round(perc*100,1)} % - ETA {eta_hour}:{eta_min}:{eta_sec} - {path}" + " "*30, end="\r")
        try:
            process_file(path)
        except Exception as e:
            logging.debug(e)
            continue
        
def process_file(path):
    t = TrackAnalyser(path)
    if not t.check_track_sanity():
        logging.debug(f"{path} is not safe to extract data from")
        return None
    t.process()
    ga_filt = [val for pos, val in enumerate(t.glide_angles) if t.glide_mask[pos] == 1]
    return ga_filt

if __name__ == "__main__":
    main()