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

input_file = "../data/full/flights_post_processed.dat"

with open(input_file, "r") as f:
    wings = pickle.load(f)

class WingDetails:
    def __init__(self):
        self.cache_dir = "./cache"
        self.cache_filename = 'wing_details.dat'
        self.cache_file = os.path.join(self.cache_dir,self.cachefile)
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
            name = re.compile("avec une (.*) \| Parapente").findall(soup.find('title').text)[0]
            try:
                clas = soup.tbody.find("tr").findAll("td")[9].a.font.text
            except AttributeError:
                clas = "O"
            self.cache[wing_id] = (name, clas)
        return self.cache[wing_id]

wd = WingDetails()
wd.load_cache()
data = []
nbw = len(wings)
for now, wid in enumerate(wings):
    if wings[wid]['dev'] > 3:
        continue
    if math.isnan(wings[wid]['dev']) or math.isnan(wings[wid]['mean']):
        continue
    print(wid, "-", end = "")
    name, clas = wd.get_wing_details(int(wid))
    print(f"{now}/{nbw} - {name}")
    data.append((
        int(wid), #0
        name, #1
        clas, #2
        utils.ga2gr(wings[wid]['mean']), #3
        max(0, utils.ga2gr(wings[wid]['mean'] + wings[wid]['dev']) - utils.ga2gr(wings[wid]['mean'])), #4, upper error
        max(0, utils.ga2gr(wings[wid]['mean']) - utils.ga2gr(wings[wid]['mean'] - wings[wid]['dev'])) #5, lower error
    ))
wd.write_cache()
data.sort(key = lambda x : x[3])

lower_error = [i[5] for i in data]
upper_error = [i[4] for i in data]
height = [i[3] for i in data]
names = [i[1] for i in data]

plt.subplots_adjust(bottom=0.3)
plt.bar(list(range(len(data))), height, yerr = (lower_error, upper_error), tick_label=names)
plt.xticks(rotation=90)
plt.show()