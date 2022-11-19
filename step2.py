"""
Realizes a statistical study over the glide angles calculated before 
in order to extract for each wing the average glide angle
as well as the standard deviation
"""

from bs4 import BeautifulSoup
import requests
import json
import re
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)

flight_analysis_file = "../data/full/flights_analysed.json"
output_file = "../data/full/flights_post_processed.json"

def get_wing_details(wing_id):
    html = requests.get("https://parapente.ffvl.fr/cfd/liste/aile/" + str(wing_id)).text
    soup = BeautifulSoup(html, 'html.parser')
    name = re.compile("avec une (.*) \| Parapente").findall(soup.find('title').text)[0]
    clas = soup.tbody.find("tr").findAll("td")[9].a.font.text
    return name, clas

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
        for flight_id in wings_to_flight[wing_id]:
            f = flights[flight_id]
            ga = f['glide_angles']
            sampling = f['sampling']
            sum_av += np.sum(ga)*sampling
            sum_sq += np.sum(ga**2)*sampling
            weight += sampling*len(ga)
            if no_iter % 100:
                logging.info(f"{round(no_iter/total_flights_to_analyse*100,1)} %")
            no_iter += 1
        wings_perf[wing_id]['mean'] = sum_av/weight
        wings_perf[wing_id]['dev'] = ((sum_sq/weight) - (sum_av/weight)**2)**(1/2)

    with open(output_file, "w") as f:
        json.dump(wings_perf, f)

def main():
    logging.info("Loading flight file")
    with open(flight_analysis_file, "r") as f:
        flights = json.load(f)
    post_process_analysis(flights)

if __name__ == "__main__":
    main()