# Scope and limitations

## Implemented and verified

Tier A: configurable pure Python synthetic mobility and channel, rectangular geometry, four
policies, delayed handover state machine, metrics, repeatable experiments E1-E6, PNG figures
F1-F5, offline interactive reports, test suite and CI configuration. Additional implemented
features: multiple vehicles, temporary blockers, strict canonical CSV replay, forecast-error
sensitivity, and SQLite persistence. CI is configured; a remote CI success badge is not claimed.

## Optional tiers not implemented

No SUMO executable/TraCI exporter or ns-3/5G-LENA backend is shipped or claimed as tested.
CSV interchange can replay independently generated mobility but is **not** an implemented
SUMO integration or synchronized co-simulation. No packet delivery, latency, real throughput,
RSRP, SINR or live network handover is reported. T24 / experiment E8 / figure F6 require an
actual compiled and validated network simulator and are outside this submission's Tier A.

To extend Tier B, follow the official SUMO installation and TraCI references, export ordered
observations in the documented CSV schema, verify frame/tick alignment, and compare replayed
positions against the original source. Record the executable and Python package versions.
For Tier C first choose a version-compatible ns-3/5G-LENA pair from official release notes;
compile its native examples, record packet traces and validate native handovers. Only then
add version-specific predictive control. No unverified integration scaffolding is included.

## Model limitations

There is no 3D propagation, ray tracing, scheduler, interference, antenna steering, beam
management, per-cell capacity, packet traffic, RRC signaling, fading correlation, realistic
sensor stack, acceleration, lane changing, learned trajectory prediction or real vehicle
control. A logical tower association is only an abstract state. Rectangles may intersect
roads/towers if deliberately configured; the validator checks shapes rather than urban realism.
No external dataset is required and no model is trained. Tower selection uses analytical look-ahead decision making.

Route projection assumes a known non-self-intersecting planned path. A current speed is held
constant in the forecast. Dynamic geometry is predicted by persistence, so unseen appearances
can defeat the predictive policy. Parameters are illustrative, not calibrated to 3GPP or
measurements. A3 is simplified, not a complete implementation of standardized measurement
events. Switches that would complete exactly at the end of the observation window remain
incomplete because that boundary is not sampled.

Results on the designated corridor are evidence only for that corridor and parameterization.
We do not tune on a hidden test set or claim broad superiority; sensitivity and ablation
results, including negative outcomes, are included. A 30-seed interval is conditional on the
toy noise distribution and does not establish performance on public roads.

## Operational limits

Reports are static, local files without accounts, cloud hosting or authentication. SQLite is
single-machine research storage; no multiuser service is intended. This project is ready for
a Tier-A software submission, not a production telecommunications deployment. Python 3.14 and 3.12 on
macOS ARM64 are tested environments; Python 3.11+ is supported by declared package
requirements and a configured CI matrix, with exact additional tested versions recorded in
the testing report. Initial dependency installation requires internet access; simulations and
reports then run offline. Native binaries/virtual environments are intentionally absent from
the portable ZIP and must be installed on a new machine with the included bootstrap script.
