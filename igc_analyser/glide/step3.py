"""
display calculated data
"""

import argparse
import math
import os
import pickle

import matplotlib.pyplot as plt
import numpy as np

from .. import utils
from ..cfd_fetcher import WingDetails


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
        "A": ("A", "#316625"),
        "bi": ("Biplace", "green"),
        "B": ("B", "#37AD00"),
        "C": ("C", "#FFB300"),
        "D": ("D", "#ba2320"),
        "K": ("CCC", "#723277"),
        "O": ("No Certification", "#000000"),
        "S": (keep_wing.title(), "blue"),  # false class for the wing we want to keep
    }

    for now, wid in enumerate(wings):
        confidence = wings[wid]["confidence"]
        mean = wings[wid]["mean"]
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
        data.append(
            (
                int(wid),  # 0
                name,  # 1
                clas,  # 2
                utils.ga2gr(mean),  # 3
                max(
                    0, utils.ga2gr(mean + confidence) - utils.ga2gr(mean)
                ),  # 4, upper error
                max(
                    0, utils.ga2gr(mean) - utils.ga2gr(mean - confidence)
                ),  # 5, lower error
            )
        )
    wd.write_cache()
    data.sort(key=lambda x: x[3])

    data = np.array(data)

    lower_error = data[:, 5]
    upper_error = data[:, 4]
    height = data[:, 3]
    names = data[:, 1]

    classes = list(classes)
    classes.sort()

    plt.figure(figsize=(9, 20), dpi=400)
    plt.subplots_adjust(left=0.3, top=0.95, bottom=0.05)

    for clas in classes:
        indexes = np.where(data[:, 2] == clas)[0]
        plt.barh(
            indexes,
            height[indexes].astype(float),
            xerr=(
                lower_error[indexes].astype(float),
                upper_error[indexes].astype(float),
            ),
            label=clas_to_name[clas][0],
            color=clas_to_name[clas][1],
        )

    plt.yticks(
        np.arange(data.shape[0]),
        names,
        rotation=0,
        horizontalalignment="right",
        fontsize=7,
    )
    plt.xlim(6.2, 8.1)
    plt.gca().invert_yaxis()
    plt.tick_params(labeltop=True)
    plt.legend()
    plt.grid(axis="x")
    plt.xlabel("Glide ratio")
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
