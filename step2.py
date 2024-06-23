"""
Realizes a statistical study over the glide angles calculated before 
in order to extract for each wing the average glide angle
as well as the standard deviation
"""

import argparse
import json
import os
import pickle

import numpy as np

import utils


def main(workdir):
    with open(utils.get_flight_json_file(workdir), "r") as f:
        flights = json.load(f)
    wings_to_flight = {}
    total_flights_to_analyse = 0
    print("Reindexing")
    for flight_id, flight in flights.items():
        if flight is None:
            continue
        if not os.path.isfile(
            utils.get_json_file_path_from_igc(workdir, flight["gps"])
        ):
            continue
        wing_id = int(flight["wing"])
        if wing_id in wings_to_flight:
            wings_to_flight[wing_id].append(flight_id)
        else:
            wings_to_flight[wing_id] = [flight_id]
        total_flights_to_analyse += 1

    wings_perf = {}
    print(
        f"Calculating average and standart deviation on {total_flights_to_analyse} flights"
    )
    no_iter = 0
    for wing_id in wings_to_flight:
        wings_perf[wing_id] = {}
        sum_av = 0
        sum_sq = 0
        weight = 0
        nb_sample = 0
        for flight_id in wings_to_flight[wing_id]:
            with open(
                utils.get_json_file_path_from_igc(workdir, flights[flight_id]["gps"]),
                "r",
            ) as f:
                flight_data = json.load(f)
            ga = np.array(flight_data["glide_angles"])
            sampling = flight_data["sampling"]
            sum_av += np.sum(ga) * sampling
            sum_sq += np.sum(ga**2) * sampling
            weight += sampling * len(ga)
            nb_sample += len(ga)
            if no_iter % 10000 == 0:
                print(f"{round(no_iter/total_flights_to_analyse*100,1)} %")
            no_iter += 1

        mean = sum_av / weight
        std_deviation = ((sum_sq / weight) - (mean) ** 2) ** (1 / 2)
        confidence_95 = (
            2 * std_deviation / nb_sample ** (1 / 2)
        )  # https://fr.wikipedia.org/wiki/Intervalle_de_confiance#Estimation_d'une_moyenne
        wings_perf[wing_id]["mean"] = mean
        wings_perf[wing_id]["dev_hist"] = std_deviation
        wings_perf[wing_id]["confidence"] = confidence_95

    print("Saving results")
    with open(utils.get_stat_file(workdir), "wb") as f:
        pickle.dump(wings_perf, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workdir", type=str, help="Work directory")
    args = parser.parse_args()

    workdir = os.path.abspath(args.workdir)

    if not os.path.isfile(utils.get_flight_json_file(workdir)):
        print("The working directory is not correct.")

    main(workdir)
