from fligt_data_analysed import flight_data as flights
wings_r = {}
for f in flights.values():
    if f is None:
        continue
    if not "wing" in f or not "glide_ratio" in f or not "glide_ratio_calc_on" in f:
        continue
    w = int(f['wing'])
    if not w in wings_r:
        wings_r[w] = {'gr': f['glide_ratio'], 'gr_on':f['glide_ratio_calc_on']}
    else:
        wings_r[w]["gr"] = (wings_r[w]["gr"]*wings_r[w]["gr_on"] + f["glide_ratio"]*f["glide_ratio_calc_on"])/(wings_r[w]["gr_on"]+f["glide_ratio_calc_on"])
        wings_r[w]["gr_on"] = wings_r[w]["gr_on"]+f["glide_ratio_calc_on"]