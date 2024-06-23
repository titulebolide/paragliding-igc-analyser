# Paragliding tracks analysis

## Todo
- [ ] investigate the source of errors in TrackAnalyser (e.g. OSError)
- [ ] investigate the source of various RuntimeWarning (divide by zero, invalide value) in igc_analyser l 94, 95, 103, 110, 112.
- [ ] Finish the refactor of the step 1, 2 and 3
- [ ] Reduce the amount of intermediary cache files (if possible)
- [ ] Find a proper metric to estimate a standard deviation of glide ratio
- [ ] Perform a first pass to estimate the hands-up speed of each paraglider
- [ ] Generalize a bit the TrackAnalyser to improve glide and thermal detection
- [ ] Add more debug graphs to TrackAnalyser
- [ ] Try to move some tuning parameters (e.g. max / min speed or turn angle) up to step 3 (or 2) for easier tuning
- [ ] Black and Isort formatting
