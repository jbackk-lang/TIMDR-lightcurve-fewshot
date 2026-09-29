# Sources and reproducibility
- Official paper: https://arxiv.org/abs/2502.02717
- Source repository: https://github.com/astromer-science/main-code
- Data link provenance: https://github.com/astromer-science/main-code/blob/main/data/get_data.sh
- Published model weights/results: https://zenodo.org/records/18207945
- Framework: https://github.com/jbackk-lang/GIA-TIMDR

This pilot uses the older public TFRecord archive linked by the official repository, not a verified reproduction of the final paper dataset. Archive test records repeat the same object IDs across class directories; labels are read from records, never inferred from directory names. Class Other (label 3) is excluded; remaining labels are 0 CB, 1 DB, 2 Mira, 4 Pulse. Training and validation labels are combined to make 20/class, without hyperparameter tuning. Full test after deduplication is used. First 200 chronological points are used, which differs from the official neural loader. No claim of directly beating A2 is supported by this pilot.

Run download_subset.py DESTINATION, then run_pilot.py --repo TIMDR_REPO --data DESTINATION/atlas. Requires existing TIMDR dependencies. A small protobuf reader avoids importing TensorFlow; its first-record values and training record count were checked against the official TensorFlow parser. No network is trained. Saved predictions permit independent score verification. Data SHA256 hashes and object splits are in audit.json. Periods are estimated without catalog input. Protocol was saved before scores.
