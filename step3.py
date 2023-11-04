"""
display calculated data
"""

import utils
import math
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
import re
import pickle
import os
import numpy as np
import argparse


class WingDetails:
    def __init__(self):
        self.cache_dir = "./cache"
        self.cache_filename = 'wing_details.dat'
        self.cachefile = os.path.join(self.cache_dir,self.cache_filename)
        self.cache = {}
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

    def load_cache(self):
        if os.path.isfile(self.cachefile):
            with open(self.cachefile, 'rb') as f:
                self.cache = pickle.load(f)
        
    def write_cache(self):
        with open(self.cachefile, 'wb') as f:
            pickle.dump(self.cache, f)

    def get_wing_details(self, wing_id):
        wing_id = int(wing_id)
        if wing_id not in self.cache:
            html = requests.get("https://parapente.ffvl.fr/cfd/liste/aile/" + str(wing_id)).text
            soup = BeautifulSoup(html, 'html.parser')
            try:
                name = re.compile("avec une (.*) \| Parapente").findall(soup.find('title').text)[0]
            except IndexError:
                name = "Unknown"
            try:
                clas = soup.tbody.find("tr").findAll("td")[9].a.font.text
            except AttributeError:
                clas = "O"
            # fix for wid 1294
            if clas == "bj": clas = "bi"
            self.cache[wing_id] = (name, clas)
        return self.cache[wing_id]


def main(infile):
    with open(infile, "rb") as f:
        wings = pickle.load(f)

    wd = WingDetails()
    wd.load_cache()
    data = []
    nbw = len(wings)
    classes = set()
    keep_wing = "hook"

    clas_to_name = {
        "A": ("A", '#316625'), 
        "bi": ("Biplace", 'green'), 
        "B": ("B", '#37AD00'), 
        "C": ("C", '#FFB300'), 
        "D": ("D", '#ba2320'), 
        "K": ("CCC", '#723277'), 
        "O": ("No Certification", '#000000'),
        "S": (keep_wing.title(), "blue") # false class for the wing we want to keep
    }

    for now, wid in enumerate(wings):
        confidence = wings[wid]['confidence']
        mean = wings[wid]['mean']
        if math.isnan(confidence):
            continue
        name, clas = wd.get_wing_details(int(wid))
        # if keep_wing in name.lower():
        #     clas = "S"
        # else:
        #     if confidence > 0.008:
        #         continue
        #     if clas not in clas_to_name:
        #         print("Unknown class", clas)
        #         continue
        classes.add(clas)
        print(f"{now}/{nbw} - {name} (#{wid})")
        data.append((
            int(wid), #0
            name, #1
            clas, #2
            utils.ga2gr(mean), #3
            max(0, utils.ga2gr(mean + confidence) - utils.ga2gr(mean)), #4, upper error
            max(0, utils.ga2gr(mean) - utils.ga2gr(mean - confidence)) #5, lower error
        ))
    wd.write_cache()
    data.sort(key = lambda x : x[3])

    data = np.array(data)

    lower_error = data[:,5]
    upper_error = data[:,4]
    height = data[:,3]
    names = data[:,1]

    classes = list(classes)
    classes.sort()

    plt.figure(figsize=(9,20), dpi=400)
    plt.subplots_adjust(left=0.3,top=0.95, bottom=0.05)

    for clas in classes:
        indexes = np.where(data[:,2] == clas)[0]
        plt.barh(
            indexes,
            height[indexes].astype(float),
            xerr = (lower_error[indexes].astype(float), upper_error[indexes].astype(float)),
            label = clas_to_name[clas][0],
            color = clas_to_name[clas][1]
        )

    plt.yticks(np.arange(data.shape[0]),names, rotation=0, horizontalalignment="right", fontsize=7)
    plt.xlim(6.2, 8.1)
    plt.gca().invert_yaxis()
    plt.tick_params(labeltop=True)
    plt.legend()
    plt.grid(axis='x')
    plt.xlabel('Glide ratio')
    plt.savefig("graph.png")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workdir", type=str, help="Working directory")
    args = parser.parse_args()

    infile = utils.get_stat_file(args.workdir)

    if not os.path.exists(infile):
        print("The input file does not exits. Exiting.")
        exit(1)

    main(infile)
