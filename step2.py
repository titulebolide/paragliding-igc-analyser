"""
Realizes a statistical study over the glide angles calculated before 
in order to extract for each wing the average glide angle
as well as the standard deviation
"""

import json
import pickle
import logging
import numpy as np
import argparse
import os
import utils

logging.basicConfig(level=logging.INFO)

input_file = "../data/full/flights_analysed.json"
output_file = "../data/full/flights_post_processed.dat"

def post_process_analysis(flights):
    wings_to_flight = {}
    total_flights_to_analyse = 0
    logging.info("Reindexing")
    for id,f in flights.items():
        if f is None:
            continue
        if not "wing" in f or not "glide_angles" in f or not "sampling" in f:
            continue
        wing_id = int(f["wing"])
        if wing_id in wings_to_flight:
            wings_to_flight[wing_id].append(id)
        else:
            wings_to_flight[wing_id] = [id]
        total_flights_to_analyse += 1

    wings_perf = {}
    logging.info(f"Calculating average and standart deviation on {total_flights_to_analyse} flights")
    no_iter = 0
    for wing_id in wings_to_flight:
        wings_perf[wing_id] = {}
        sum_av = 0
        sum_sq = 0
        weight = 0
        nb_sample = 0
        for flight_id in wings_to_flight[wing_id]:
            f = flights[flight_id]
            ga = np.array(f['glide_angles'])
            sampling = f['sampling']
            sum_av += np.sum(ga)*sampling
            sum_sq += np.sum(ga**2)*sampling
            weight += sampling*len(ga)
            nb_sample += len(ga)
            if no_iter % 10000 == 0:
                logging.info(f"{round(no_iter/total_flights_to_analyse*100,1)} %")
            no_iter += 1

        mean = sum_av/weight
        std_deviation = ((sum_sq/weight) - (mean)**2)**(1/2)
        confidence_95 = 2*std_deviation/nb_sample**(1/2) # https://fr.wikipedia.org/wiki/Intervalle_de_confiance#Estimation_d'une_moyenne
        wings_perf[wing_id]['mean'] = mean
        wings_perf[wing_id]['dev_hist'] = std_deviation
        wings_perf[wing_id]['confidence'] = confidence_95

    return wings_perf


def main(infile, outfile):
    logging.info("Loading flight file")
    with open(infile, "r") as f:
        flights = json.load(f)

    wings_perf = post_process_analysis(flights)

    logging.info("Saving results")
    with open(outfile, "wb") as f:
        pickle.dump(wings_perf, f)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", type=str, help="Input file")
    parser.add_argument("outfile", type=str, help="Output file")
    args = parser.parse_args()

    infile = os.path.abspath(args.infile)
    outfile = os.path.abspath(args.outfile)

    if not os.path.isfile(infile):
        print("The input file does not exits. Exiting.")
        exit(1)

    if not infile.endswith(".json"):
        print("The input file must be a JSON file. Exiting.")
        exit(1)

    if not outfile.endswith(".json"):
        print("The output file must ends with the json extension. Exiting.")
        exit(1)

    if os.path.exists(outfile):
        if not utils.yesno("This file already exists. Override?", default_yes=False):
            print("Exiting.")
            exit(0)

    if not os.path.isdir(os.path.dirname(outfile)):
        print(f"{os.path.dirname(outfile)} is not a valid directory. Exiting.")
        exit(1)

    main(infile, outfile)
