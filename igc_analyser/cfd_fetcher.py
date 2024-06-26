"""
Scrapes the FFVL website in order to gather the necessary data
"""

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings()
import argparse
import concurrent.futures
import datetime as dt
import json
import os
import pickle
import re
import sys
import time
import traceback

from progress.bar import Bar

from . import utils


class WingDetails:
    def __init__(self):
        self.cache_dir = "./cache"
        self.cache_filename = "wing_details.dat"
        self.cachefile = os.path.join(self.cache_dir, self.cache_filename)
        self.cache = {}
        if not os.path.isdir(self.cache_dir):
            os.makedirs(self.cache_dir)

    def load_cache(self):
        if os.path.isfile(self.cachefile):
            with open(self.cachefile, "rb") as f:
                self.cache = pickle.load(f)

    def write_cache(self):
        with open(self.cachefile, "wb") as f:
            pickle.dump(self.cache, f)

    def get_wing_details(self, wing_id):
        wing_id = int(wing_id)
        if wing_id not in self.cache:
            html = requests.get(
                "https://parapente.ffvl.fr/cfd/liste/aile/" + str(wing_id)
            ).text
            soup = BeautifulSoup(html, "html.parser")
            try:
                name = re.compile(r"avec une (.*) | Parapente").findall(
                    soup.find("title").text
                )[0]
            except IndexError:
                name = "Unknown"
            try:
                clas = soup.tbody.find("tr").findAll("td")[9].a.font.text
            except AttributeError:
                clas = "O"
            # fix for wid 1294
            if clas == "bj":
                clas = "bi"
            self.cache[wing_id] = (name, clas)
        return self.cache[wing_id]


def get_ffvl_no_dns(url):
    return requests.get(
        f"https://54.36.26.32/{url}",
        headers={"Host": "parapente.ffvl.fr"},
        verify=False,
    )


def get_all_flights_in_page(page):
    url = f"https://parapente.ffvl.fr/cfd/liste?page={page}&sort=desc&order=date"
    html = requests.get(url).text
    with open("test.hml", "w") as f:
        f.write(html)
    soup = BeautifulSoup(html, "html.parser")
    ids = []
    first_id = -1
    for noline, line in enumerate(soup.find(id="content").findAll("tr")[1:]):
        id = int(line.td.a["href"].split("/")[-1])
        if line.findAll("td")[0].font is None:
            ids.append(id)
        if noline == 0:
            first_id = id
    assert first_id != -1
    return ids, first_id


def get_all_flights(max_page=-1):
    page = 0
    done = False
    ids = []
    last_first_id = -1
    while not done:
        print(page)
        ids_temp, first_id = get_all_flights_in_page(page)
        if first_id == last_first_id:
            # reached the end
            done = True
            break
        last_first_id = first_id
        ids.extend(ids_temp)
        page += 1
        if page > max_page:
            break
    return ids


def _is_wing_url(href):
    if href is None:
        return False
    return href.startswith("https://parapente.ffvl.fr/cfd/liste/aile/")


def _is_flight_url(href):
    if href is None:
        return False
    return href.startswith("/sites/parapente.ffvl.fr/files/igcfiles/")


def get_single_flight_data(flight_id, workdir, batch_no):
    url = f"/cfd/liste/vol/{flight_id}"
    html = None
    while html is None:
        try:
            html = get_ffvl_no_dns(url).text
        except requests.RequestException:
            html = None
            print(f"Failed to pull id {flight_id}, retrying in 5s")
            time.sleep(5)
    soup = BeautifulSoup(html, "html.parser").find(id="block-system-main")
    gps_track = soup.find(href=_is_flight_url)
    wing_id = soup.find(href=_is_wing_url)
    if gps_track is None or wing_id is None:
        return None
    gps_track = gps_track["href"].split("/")[-1]
    wing_id = wing_id["href"].split("/")[-1]

    igcfile_path = os.path.join(utils.get_track_save_dir(workdir, batch_no), gps_track)
    get_single_flight_track(gps_track, igcfile_path)
    return {"gps": os.path.join(str(batch_no), gps_track), "wing": wing_id}


def get_single_flight_track(filename, path):
    url = f"/sites/parapente.ffvl.fr/files/igcfiles/{filename}"
    igcfile = None
    while igcfile is None:
        try:
            igcfile = get_ffvl_no_dns(url).text
        except requests.RequestException:
            igcfile = None
            print(f"Failed to pull id {filename}, retrying in 5s")
            time.sleep(5)
    with open(path, "w") as f:
        f.write(igcfile)


def get_flight_data(outdir, ids, batch_size=1000, save_data=True):
    bar = Bar(
        "Processing",
        max=len(ids),
        suffix="%(percent).1f %% -- %(elapsed)d s -- %(eta)d s",
    )
    flight_data = {}
    for batch_no in range(0, len(ids) // batch_size + 1):
        os.makedirs(utils.get_track_save_dir(outdir, batch_no))
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = {}
            for id in ids[batch_no * batch_size : (batch_no + 1) * batch_size]:
                future = executor.submit(
                    lambda x: get_single_flight_data(x, outdir, batch_no), id
                )
                future.add_done_callback(lambda x: bar.next())
                futures[id] = future
            try:
                for id, future in futures.items():
                    try:
                        res = future.result()
                    except Exception as e:
                        print(
                            f"An error happend while retreiving the data : {''.join(traceback.format_exception(*sys.exc_info()))}"
                        )
                    flight_data[id] = res

            except KeyboardInterrupt:
                bar.finish()
                for future in futures.values():
                    future.cancel()
                break

        with open(os.path.join(outdir, "flight_data.json"), "w") as f:
            json.dump(flight_data, f)

    bar.finish()
    return flight_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--workdir",
        type=str,
        default="",
        help="The directory where to save the data.",
    )
    args = parser.parse_args()

    outdir = args.workdir

    if outdir == "":
        strtime = dt.datetime.strftime(dt.datetime.now(), "%Y%m%d_%H%M%S")
        outdir = os.path.join(".", f"{strtime}_ffvl_data_extractor")

    outdir = os.path.abspath(outdir)

    if os.path.exists(outdir):
        print(f"{outdir} already exists. Exiting.")
        exit(1)

    os.makedirs(outdir)

    print("Step 1 : Getting all flight ids")
    ids = get_all_flights(0)
    print(ids)
    print("Step 2 : Getting all flight datas")
    get_flight_data(outdir, ids)
    print("Done")
    exit(0)
