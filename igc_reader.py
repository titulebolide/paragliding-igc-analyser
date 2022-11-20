import datetime as dt
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d
import numpy as np

class IGCReader:
    def __init__(self, filename):
        self.filename = filename
        self.date = None
        self.data_formated = []
        with open(filename, "r") as f:
            for rec in f.readlines():
                self.read_record(rec)
        self.data_formated = np.array(self.data_formated)
        self.timestamp = self.data_formated[:,0]
        self.latitude = self.data_formated[:,1]
        self.longitude = self.data_formated[:,2]
        self.altitude_gnss = self.data_formated[:,3]
        self.altitude_baro = self.data_formated[:,4]

    def read_record(self, rec):
        if rec.startswith("B"):
            self.read_b_record(rec)
        elif rec.startswith("H"):
            self.read_h_record(rec)

    def read_b_record(self, rec):
        time = int(dt.datetime(
            year=self.day.year, 
            month=self.day.month, 
            day=self.day.day,
            hour=int(rec[1:3]),
            minute=int(rec[3:5]),
            second=int(rec[5:7])
        ).timestamp())
        if len(rec) < 35:
            raise OSError("Truncated record")
        if not rec[14] in ("S", "N") or not rec[23] in ("E", "W"):
            raise OSError("Can't decode data")
        lat = int(rec[7:9]) + int(rec[9:14])/1000/60
        if rec[14] == "S":
            lat = -lat
        lon = int(rec[15:18]) + int(rec[18:23])/1000/60
        if rec[23] == "0":
            lon = -lon
        gnss_alt = int(rec[25:30])
        baro_alt = int(rec[30:35])
        self.data_formated.append((time, lat, lon, gnss_alt, baro_alt))
    
    def read_h_record(self, rec):
        if rec.startswith("HFDTE"):
            if rec.startswith("HFDTEDATE"):
                rec = rec[5:]
            try:
                self.day = dt.date(day=int(rec[5:7]), month=int(rec[7:9]), year=2000+int(rec[9:11]))
            except ValueError as e:
                print(f"{e}, filling with 01/01/2000")
            self.day = dt.date(day=1, month=1, year=2000)
             
    def display_track(self):
        ax = plt.figure().add_subplot(projection='3d')
        ax.plot(
            self.latitude,    
            self.longitude,    
            self.altitude_baro,    
        )
        plt.show()
        plt.plot(self.altitude_gnss)
        plt.plot(self.altitude_baro)
        plt.show()

    def _get_data_index(noindex):
        return [p[noindex] for p in self.data_formated]

    def mean_time_delta(self):
        return np.mean(np.diff(self.timestamp))
        
