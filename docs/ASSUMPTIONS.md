# Units, denominators and experimental assumptions

* Positions/distance are meters, time is seconds, speed is m/s, heading is radians.
* Power is a synthetic log-distance **dBm proxy**, not measured RSRP. Gains are dBi, losses dB.
* Observation times are `0, dt, ..., duration-dt`. Duration and horizon must be integral tick
  multiples. No extra endpoint sample is included in metric denominators.
* Each active configured synthetic vehicle exists for the entire interval, including after stopping.
  Vehicles can be disabled with `active: false`; at least one active vehicle is required.
  CSV trace vehicles may depart permanently. Only their observed ticks count.
* All policies share initial strongest-usable attachment, current channel, trace, seed,
  thresholds, handover delay, and dwell. Only their recommendation logic differs.
* Initial access/recovery is instantaneous and tracked separately from delayed handovers.
* Temporary blockers occupy `[start_s, end_s)`; forecasts use current geometry persistence.
  Multiple intersecting blockers incur one penalty, not a sum of penalties.
* The radio model is `tx + tx_gain + rx_gain - pl0 - 10*n*log10(max(d,d0)/d0)
  - blockage_penalty + keyed_shadowing`. Enabled links at or above threshold are usable.
* Shadowing draws are independent per tower/vehicle/time key. They have no temporal or spatial
  correlation. Actual zero-noise scenarios do not gain statistical information from more seeds.
* Predictive quality is the arithmetic mean of clamped dBm values, not linear received power.
  All scoring weights, normalization bounds, gates and penalties are in YAML.
* Nearest can nominate an unusable target; rejection is neither an attempted switch nor success.
* Outage fraction = outage vehicle-observations / observed vehicle-observations. Outage means
  switching, disconnected, missing serving link, or serving link below threshold.
* Outage seconds = outage steps * dt (vehicle-seconds for multiple vehicles). Episodes are per
  vehicle, reset on recovery, and include final unfinished outages. Mean/worst episode use them.
* Coverage = 1 - outage with the same denominator. Quality mean uses usable ATTACHED rows only,
  with its sample count; it is null if no such samples exist.
* Completed handovers count `success`, attempts count `attempted`, execution failures count
  `failed`, invalid nominations count `rejected`, and terminal requests count `incomplete`.
* Ping-pong counts each consecutive completed A->B->A return inside the configured window
  once, independently per vehicle. Initial/recovery attachments do not count as handovers.
* Switch interruption is observed SWITCHING steps * dt, capped by the observation window;
  it may exceed the configured non-integral delay by less than one dt per switch.
* `duration_s` in metrics is the final recorded timestamp plus dt, not summed vehicle time.
  `observed_vehicle_seconds` provides the summed exposure.
* E2 covers the complete route at each speed plus 5 seconds stationary, rounding duration up
  to a tick. This holds traveled geometry constant; time exposure necessarily changes.
* E5 location error is isotropic forecast displacement (standard deviation per axis), not
  simulated sensor error in actual positions. No true channel sample is changed.
* Paired differences are predictive minus strongest-current outage fractions; negative favors
  predictive. A percentage-point effect is 100 times this difference. Relative improvement
  uses the baseline mean as denominator and is undefined for zero baseline outage.
* Bootstrap intervals resample paired seed differences with fixed bootstrap RNG seed 2026,
  10,000 draws and percentile bounds. They describe this model/scenario/seeding procedure,
  not real-world uncertainty or a correction for exploring many variants.
