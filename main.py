from igc_reader import IGCReader
import matplotlib.pyplot as plt
import math
import numpy as np
import time
from haversine import haversine

def ga2gr(ga):
    if ga == 0:
        return 1000000
    return -1/math.tan(ga/180*math.pi)

def gr2ga(gr):
    return math.atan(-1/gr)/math.pi*180

class TrackAnalyser:
    def __init__(
        self, 
        filename, 
        frame_len_sec = 20, 
        max_turn = 10, 
        min_speed = 25, 
        min_sec = 20
    ):
        self.filename = filename
        self.track = IGCReader(filename)
        self.track_mean_time_delta = self.track.mean_time_delta()
        if not self.check_track_sanity():
            print("Track not safe to extract data from")
            return
        self.process_track(frame_len_sec=frame_len_sec)
        self.calc_glide_moments(max_turn=max_turn, min_speed=min_speed, min_sec=min_sec)

    def check_track_sanity(self):
        if self.track_mean_time_delta > 4:
            return False
        return True

    def process_track(self, frame_len_sec):
        frame_len = round(frame_len_sec/self.track_mean_time_delta)
        glide_angle = []
        glide_angle_m = [0] #sweeping mean
        turn = []
        cum_turn = [0]
        cur_heading = 0
        straight_line_speed = []
        timestamps = []
        cum_distance = [0]
        for i in range(0,len(self.track.timestamp)-1):
            diff_lat = self.track.latitude[i+1] - self.track.latitude[i]
            diff_lon = self.track.longitude[i+1] - self.track.longitude[i]
            ver_dist = self.track.altitude_gnss[i+1] - self.track.altitude_gnss[i]
            hor_dist = haversine((self.track.latitude[i], self.track.longitude[i]), (self.track.latitude[i+1], self.track.longitude[i+1]))*1000

            cum_distance.append(cum_distance[-1] + hor_dist)

            if hor_dist == 0:
                continue #TODO: change this

            prev_heading = cur_heading
            cur_heading = 0
            if diff_lat != 0:
                cur_heading = math.atan(diff_lon/diff_lat)/math.pi*180
            if diff_lon < 0:
                cur_heading += 180
            if cur_heading < 0:
                cur_heading += 360

            timestamps.append(self.track.timestamp[i+1]-self.track.timestamp[0])
            current_turn = cur_heading - prev_heading
            current_turn = (current_turn + 180)%360 - 180
            turn.append(current_turn)
            glide_angle.append(math.atan(ver_dist/hor_dist)/math.pi*180)

            if len(glide_angle) >= frame_len+1:
                glide_angle_m.append(glide_angle_m[-1]+(glide_angle[-1]-glide_angle[-frame_len-1])/frame_len)
                cum_turn.append((cum_turn[-1]*(self.track.timestamp[i]-self.track.timestamp[i-frame_len])+turn[-1]-turn[-frame_len-1])/(self.track.timestamp[i+1]-self.track.timestamp[i+1-frame_len]))
                straight_line_speed.append(
                    haversine(
                        (self.track.latitude[i+1], self.track.longitude[i+1]),
                        (self.track.latitude[i+1-frame_len], self.track.longitude[i+1-frame_len])
                    )*1000 / (self.track.timestamp[i+1]-self.track.timestamp[i+1-frame_len])
                )
            else:
                glide_angle_m.append((glide_angle_m[-1]*(len(glide_angle)-1)+glide_angle[-1])/len(glide_angle))
                cum_turn.append((cum_turn[-1]*(self.track.timestamp[i]-self.track.timestamp[0]) + turn[-1])/(self.track.timestamp[i+1]-self.track.timestamp[0]))
                straight_line_speed.append(
                    haversine(
                        (self.track.latitude[i+1], self.track.longitude[i+1]), 
                        (self.track.latitude[0], self.track.longitude[0])
                    )*1000 / (self.track.timestamp[i+1]-self.track.timestamp[0])
                )

        self.timestamps = np.array(timestamps)
        self.glide_angles_instantaneous = np.array(glide_angle)
        self.glide_angles = np.array(glide_angle_m[1:])
        self.turn_speeds = np.array(cum_turn[1:])
        self.straight_line_speeds = np.array(straight_line_speed)
        self.cumulative_distance = np.array(cum_distance)

    def calc_glide_moments(self, max_turn, min_speed, min_sec):
        min_iter = round(min_sec/self.track_mean_time_delta)

        mask = (
            self.turn_speeds < max_turn
        ).astype(int)*(
            self.straight_line_speeds > min_speed/3.6
        ).astype(int)*(
            self.glide_angles < gr2ga(15)
        ).astype(int)*(
            self.glide_angles > gr2ga(2)
        ).astype(int)

        mask_filtered = []
        current_on_begin = None
        for i, elt in enumerate(mask):
            if elt == 1 and current_on_begin is None:
                current_on_begin = i
            if elt == 0 and current_on_begin is not None:
                len_mask_on = i - current_on_begin
                if len_mask_on > min_iter:
                    mask_filtered += [1]*len_mask_on
                else:
                    mask_filtered += [0]*len_mask_on
                current_on_begin = None
            if elt == 0:
                mask_filtered.append(0)
        self.glide_mask = mask_filtered

    def get_glide_ratio(self):
        ga_filt = [val for pos, val in enumerate(self.glide_angles) if self.glide_mask[pos] == 1 and val < 0]
        gr = -1/math.tan(sum(ga_filt)/len(ga_filt)/180*math.pi)
        return gr

    def plot_height_vs_distance(self):
        pass

    def __len__(self):
        return self.timestamps.shape[0]

    def plot_glide_ratio_histogram(self):
        counts, bins = np.histogram([ga2gr(ga) for pos, ga in enumerate(self.glide_angles) if self.glide_mask[pos] == 1], 50, [-15, 15])
        plt.stairs(counts, bins)
        plt.legend()
        plt.show()


#filename = "../data/partial/igcfiles/0/2003-07-06-0470-0.igc"
#filename = "../data/partial/igcfiles/0/2002-04-19-0138-0.igc"
#filename = "../data/partial/igcfiles/0/2022-10-26-igcfile-135741-256019.igc"
#filename = "../data/partial/igcfiles/0/2022-10-27-igcfile-203670-256022.igc"
#filename = "../data/partial/igcfiles/0/2022-10-27-igcfile-14905042-256016.igc"
filename = "../data/partial/igcfiles/0/2022-10-28-igcfile-16038-256023.igc"

t = TrackAnalyser(filename)
print(t.get_glide_ratio())
t.plot_glide_ratio_histogram()

if False:
    plt.subplot(411)
    plt.plot(t.track.timestamp, t.track.altitude_gnss)
    plt.subplot(412)
    plt.plot(t.cumulative_distance, t.track.altitude_gnss)
    plt.subplot(413)
    plt.plot(t.timestamps,t.turn_speeds)
    plt.subplot(414)
    plt.plot(t.timestamps,t.straight_line_speeds*3.6)
    plt.show()

if True:
    plt.subplot(411)
    plt.plot(t.track.timestamp, t.track.altitude_gnss)
    plt.subplot(412)
    plt.plot(t.cumulative_distance, t.track.altitude_gnss)
    plt.subplot(413)
    plt.plot(t.timestamps,t.glide_mask)
    plt.subplot(414)
    plt.plot([0]*len(t.timestamps), 'black')
    plt.plot(t.timestamps,t.glide_angles)
    plt.show()

if False:
    counts, bins = np.histogram([-1/math.tan(d["ga_m"][i]/180*math.pi) for i in range(len(d["ga"])) if mask_filtered[i] == 1], 50, [-15, 15])
    plt.stairs(counts, bins, label="d3_m")
    plt.legend()
    plt.show()

if False:
    ga_filt = [d["ga_m"][i] for i in range(len(d["ga"])) if mask_filtered[i] == 1 and d["ga_m"][i] < 0]
    gr = -1/math.tan(sum(ga_filt)/len(ga_filt)/180*math.pi)
    print(gr)