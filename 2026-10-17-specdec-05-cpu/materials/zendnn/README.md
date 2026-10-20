# ZenDNN llama-bench outputs

Source: local copies of `bench_results.csv` and the corresponding `llama-bench` text outputs from the CT115 ZenDNN experiment, dated 2026-10-20. These files contain benchmark results only; no server launch configuration, credentials, host inventory, or service logs are included.

`bench_results.csv` contains 28 rows for Qwen3.5-9B, YandexGPT-5-Lite-8B, and Gemma 4 E4B across ZenDNN and ggml-cpu backends. The reported llama-bench runs use two repetitions. `err` is preserved as emitted by the harness; do not treat two repetitions as a stable estimate of deployment performance.

The two files ending in `d29796.txt` are empty outputs from the attempted long-context run. The experiment log reports that the run did not yield parseable benchmark rows; these files are retained as evidence of the incomplete measurement, not as a performance result.

The CSV's `rawfile` column points to the original temporary benchmark directory. Local filenames were preserved here; the values in that column are unchanged from the collected CSV.
