# TIMDR light curves: frozen pilot protocol v1

Written before downloading light curves or inspecting classification scores, 2026-09-29.
This is a local timestamped protocol, not an externally registered study.

## Question
Does a TIMDR-inspired phase/coherence representation improve macro-F1 with 4–160 labeled stars per class, compared with classical features and a directly sampled phase curve? No positive outcome is assumed. This is closed-set classification, not discovery of unknown classes.

## Data and separation
Public OGLE-IV LMC I-band photometry: RRab, RRc, classical Cepheid F and 1O. Random candidate order seed 20260929, select 500 eligible unique stars/class: 300 support-pool and 200 test stars. At least 80 finite observations with positive uncertainty; remove exact repeated timestamps by inverse-variance averaging. Deduplicate exact photometry hashes and positions within 2 arcsec globally. Require >=75% occupied bins among 32 phase bins. Report exclusions. No catalog magnitudes, colors, Fourier coefficients or epoch-of-maximum are classifier inputs. Period is catalog-supplied to ALL methods (oracle-period experiment). Individual normalization and unsupervised curve extraction may use a star's own complete observations. No test-label feature selection or tuning.

## Representation frozen before scores
Fit weighted 8-harmonic Fourier model to robustly centered/scaled magnitudes at catalog phase. Clip inverse variance weights at 100x their median; add fixed ridge 0.01*trace(X'WX)/dimension. Phase origin is the fitted fundamental phase, not the catalog epoch. Sample 64 evenly spaced phases.
TIMDR-inspired adaptation: split chronologically into four observation groups; fit the same harmonics. Their agreement defines harmonic coherence |mean(complex coefficient)| / RMS(amplitude). Coherence squared is the sieve weight on each full-curve harmonic, producing a 64-point filtered phase template. Add 8 coherences and 8 relative harmonic amplitudes. This is a new experimental M/S adaptation, NOT the original bearing carrier-band algorithm or a proven TIMDR theorem. No geometric/modal branch claims.

## Arms
All receive log10(period), log10(robust amplitude), log10(median error/amplitude).
1. Period only + shrinkage LDA (control).
2. Classical features + random forest (200 trees, min_samples_leaf=2, balanced).
3. Classical features + same shrinkage LDA (fair classifier control).
4. Unfiltered 64-point phase template + LDA.
5. TIMDR-inspired filtered template/coherence/amplitudes + LDA.
6. Unfiltered phase template + small MLP (64 hidden tanh units, alpha=1, lbfgs, max_iter=400).
7. Filtered template only + LDA (ablation: isolate filtering from extra features).
Classical: amplitude, period, relative measurement noise, robust skew/kurtosis, 8 harmonic amplitudes relative to first, sin/cos of invariant phases phi_k-k*phi_1, Fourier residual RMS, successive-difference ratio. LDA uses standardized training features and covariance shrinkage=0.2. Scaling fitted only to labeled support stars. Fixed settings; no validation labels or hyperparameter search.

ASTROMER pretrained comparison is a separate extension: audit runtime/weights/pretraining overlap first. If not executed, explicitly mark missing and prohibit claims of superiority over pretrained networks.

## Evaluation
Budgets [4,8,16,32,64,128,160] per class; 30 paired nested support draws from 300-star pool, seeds 10000..10029. Fixed 800-star test set. Report macro-F1, per-class recall and paired deltas. 95% intervals over draws describe support-selection variability, not independent test-population uncertainty. Primary endpoint: average paired difference across budgets 4,8,16,32 vs classical RF. Practical target +0.02 macro-F1; report paired bootstrap interval across 30 draws (10,000 resamples, seed 99). Also compare against phase+LDA; success against RF alone does not establish sieve benefit. Paired star-bootstrap at budget 4 checks finite test-set uncertainty, keeping draws paired.

Negative control: 30 shuffled support-label runs of TIMDR at n=32, test labels unchanged. Additional diagnostic: period perturbed +1% for ALL representations (same support stars, n=4,32,160; first 5 draws); this is clock sensitivity, not period recovery. No result-dependent feature revisions in this version.

## Boundaries
No claim of 8x label efficiency without measured target crossing; no orbital velocity estimation, no telescope connection. In-distribution LMC pilot; real period recovery, different-survey transfer, rare-class discovery, pretrained comparison remain separate milestones. Catalog labels/periods are not an independent astrophysical truth oracle. Publish negative findings and exact sample IDs, software versions, protocol hash, predictions and seeds.
