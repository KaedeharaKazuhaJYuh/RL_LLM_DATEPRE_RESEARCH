# V3.1 real-data provenance

The committed CSV files are deterministic 240-row extracts prepared by `research/v3_real_data.py` from official UCI archives. Archive and derived-file SHA-256 values are pinned in `manifest.json`.

| Dataset | Use | UCI DOI | License |
|---|---|---|---|
| Wine Quality | recovery training | https://doi.org/10.24432/C56S3T | CC BY 4.0 |
| Bank Marketing | recovery training | https://doi.org/10.24432/C5K306 | CC BY 4.0 |
| Abalone | frozen recovery test | https://doi.org/10.24432/C55C7W | CC BY 4.0 |
| Seoul Bike Sharing Demand | frozen recovery test | https://doi.org/10.24432/C5F62R | CC BY 4.0 |
| Bike Sharing | frozen recovery test | https://doi.org/10.24432/C5W894 | CC BY 4.0 |

Attribution belongs to the creators listed by UCI. The extracts are redistributed under the source datasets' Creative Commons Attribution 4.0 licenses. See `manifest.json` for the exact official download URLs and hashes.
