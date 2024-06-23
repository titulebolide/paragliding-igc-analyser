from igc_reader import IGCReader
import matplotlib.pyplot as plt
import math
import numpy as np
from haversine import haversine
from utils import *

class TrackAnalyser:
    def __init__(
        self, 
        filename,
        frame_len_sec = 20, 
        max_turn = 10, 
        min_speed = 25, 
        min_sec = 20,
        max_glide_ratio = 15,
        min_glide_ratio = 2
    ):
        self.filename = filename
        self.frame_len_sec = frame_len_sec
        self.max_turn = max_turn
        self.min_speed = min_speed
        self.min_sec = min_sec
        self.max_glide_ratio = max_glide_ratio
        self.min_glide_ratio = min_glide_ratio
        self.track = IGCReader(filename)
        self.track_mean_time_delta = self.track.mean_time_delta()

    def check_track_sanity(self, use_baro = True):
        """
        checks track sanity
        returns 0 is track is sane
        returns another code depending on the reason of the insaninty
        """
        altitude = self.track.altitude_baro if use_baro else self.track.altitude_gnss
        if self.track_mean_time_delta > 6 or self.track_mean_time_delta < 0.001:
            # Bad time deltas, to high or (abnormally) negative or low
            return 1
        if np.min(np.diff(self.track.timestamp)) < 0:
            # the diff between consecutive time deltas must always be positive
            return 2
        if np.max(altitude)-np.min(altitude) < 10:
            # no meaningful altitude data
            return 3
        return 0

    def process(self, use_baro = True):
        frame_len = round(self.frame_len_sec/self.track_mean_time_delta)
        altitude = self.track.altitude_baro if use_baro else self.track.altitude_gnss
        glide_angle = []
        glide_angle_m = [0] #sweeping mean
        turn = []
        cum_turn = [0]
        cur_heading = 0
        straight_line_speed = []
        timestamps = []
        cum_distance = [0]
        self.heading = []
        for i in range(len(self.track.timestamp)-1):
            diff_lat = self.track.latitude[i+1] - self.track.latitude[i]
            diff_lon = self.track.longitude[i+1] - self.track.longitude[i]
            ver_dist = altitude[i+1] - altitude[i]
            hor_dist = haversine((self.track.latitude[i], self.track.longitude[i]), (self.track.latitude[i+1], self.track.longitude[i+1]))*1000

            cum_distance.append(cum_distance[-1] + hor_dist)

            if hor_dist == 0:
                hor_dist = 0.0000001

            prev_heading = cur_heading
            cur_heading = 0
            if diff_lat != 0:
                cur_heading = math.atan(diff_lon/diff_lat)/math.pi*180
            if diff_lon < 0:
                cur_heading += 180
            if cur_heading < 0:
                cur_heading += 360

            self.heading.append(cur_heading)

            timestamps.append(self.track.timestamp[i+1]-self.track.timestamp[0])
            current_turn = cur_heading - prev_heading
            current_turn = (current_turn + 180)%360 - 180
            turn.append(current_turn)
            glide_angle.append(math.atan(ver_dist/hor_dist)/math.pi*180)

            if i >= frame_len:
                glide_angle_m.append(glide_angle_m[-1]+(glide_angle[-1]-glide_angle[-frame_len-1])/frame_len)
                cum_turn.append(
                    (
                        cum_turn[-1]*(
                            self.track.timestamp[i]-self.track.timestamp[i-frame_len]
                        ) + turn[-1] - turn[-frame_len-1]
                    )/(
                        self.track.timestamp[i+1]-self.track.timestamp[i+1-frame_len]
                    )
                )
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
        self.turn_speeds_instantaneous = np.array(turn)
        self.straight_line_speeds = np.array(straight_line_speed)
        self.cumulative_distance = np.array(cum_distance)

    def calc_glide_mask(self):
        min_iter = round(self.min_sec/self.track_mean_time_delta)

        mask = (
            np.abs(self.turn_speeds) < self.max_turn
        ).astype(int)*(
            self.straight_line_speeds > self.min_speed/3.6
        ).astype(int)*(
            self.glide_angles < gr2ga(self.max_glide_ratio)
        ).astype(int)*(
            self.glide_angles > gr2ga(self.min_glide_ratio)
        ).astype(int)

        mask_filtered = []
        current_on_begin = None
        for i, elt in enumerate(mask):
            if elt == 1 and current_on_begin is None:
                current_on_begin = i
            if (elt == 0 or i+1 == len(mask)) and current_on_begin is not None:
                len_mask_on = i - current_on_begin
                if i+1 == len(mask):
                    len_mask_on += 1
                if len_mask_on > min_iter:
                    mask_filtered += [1]*len_mask_on
                else:
                    mask_filtered += [0]*len_mask_on
                current_on_begin = None
            if elt == 0:
                mask_filtered.append(0)

        self._unfiltered_glide_mask = mask
        self.glide_mask = mask_filtered

    def get_glide_ratio(self):
        ga_filt = [val for pos, val in enumerate(self.glide_angles) if self.glide_mask[pos] == 1]
        gr = -1/math.tan(sum(ga_filt)/len(ga_filt)/180*math.pi)
        return gr

    def plot_glide_mask_debug(self):
        plt.subplot(511)
        plt.plot(self.cumulative_distance, self.track.altitude_baro)
        plt.subplot(512)
        plt.plot(self.timestamps,self.glide_mask, 'b')
        plt.plot(self.timestamps,self._unfiltered_glide_mask, 'r')
        plt.title("Glide mask")
        plt.subplot(513)
        plt.plot([self.timestamps[0], self.timestamps[-1]], [self.max_turn]*2, 'black')
        plt.plot([self.timestamps[0], self.timestamps[-1]], [-self.max_turn]*2, 'black')
        plt.plot(self.timestamps, self.turn_speeds)
        plt.title("Turn speed")
        plt.subplot(514)
        plt.plot([self.timestamps[0], self.timestamps[-1]], [self.min_speed]*2, 'black')
        plt.plot(self.timestamps, self.straight_line_speeds*3.6)
        plt.title("Straight line speed")
        plt.subplot(515)
        plt.plot([self.timestamps[0], self.timestamps[-1]], [0,0], 'black')
        plt.plot([self.timestamps[0], self.timestamps[-1]], [gr2ga(self.max_glide_ratio)]*2, 'red')
        plt.plot([self.timestamps[0], self.timestamps[-1]], [gr2ga(self.min_glide_ratio)]*2, 'red')
        plt.plot(self.timestamps, self.glide_angles)
        plt.title("Glide angles")
        plt.show()


    def _temp_debug_turn(self):
        plt.subplot(411)
        plt.plot(self.cumulative_distance, self.track.altitude_baro)
        plt.subplot(412)
        plt.plot(self.timestamps, self.heading)
        plt.subplot(413)
        plt.plot(self.timestamps, self.turn_speeds)
        plt.subplot(414)
        plt.plot(self.timestamps, self.turn_speeds_instantaneous)
        plt.show()

    def __len__(self):
        return self.timestamps.shape[0]

    def plot_glide_ratio_histogram(self):
        counts, bins = np.histogram([ga2gr(ga) for pos, ga in enumerate(self.glide_angles) if self.glide_mask[pos] == 1], 50, [-15, 15])
        plt.stairs(counts, bins)
        plt.legend()
        plt.show()