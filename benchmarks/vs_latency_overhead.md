# VS Latency Overhead Benchmark

| Profile | Query | Baseline (ms) | VS (ms) | Overhead (%) |
|---|---|---|---|---|
| VSDeploymentProfile.LATENCY_SENSITIVE | Explain quantum computing | 103.25 | 139.92 | 35.5% |
| VSDeploymentProfile.LATENCY_SENSITIVE | What is the capital of France | 110.17 | 139.11 | 26.3% |
| VSDeploymentProfile.LATENCY_SENSITIVE | How does photosynthesis work | 109.32 | 140.13 | 28.2% |
| VSDeploymentProfile.LATENCY_SENSITIVE | Describe the water cycle | 108.45 | 143.14 | 32.0% |
| VSDeploymentProfile.LATENCY_SENSITIVE | What causes earthquakes | 108.97 | 139.56 | 28.1% |
| VSDeploymentProfile.BALANCED | Explain quantum computing | 110.79 | 139.23 | 25.7% |
| VSDeploymentProfile.BALANCED | What is the capital of France | 108.3 | 142.44 | 31.5% |
| VSDeploymentProfile.BALANCED | How does photosynthesis work | 109.11 | 139.87 | 28.2% |
| VSDeploymentProfile.BALANCED | Describe the water cycle | 109.27 | 140.1 | 28.2% |
| VSDeploymentProfile.BALANCED | What causes earthquakes | 109.26 | 139.22 | 27.4% |
| VSDeploymentProfile.MAX_ACCURACY | Explain quantum computing | 108.28 | 140.47 | 29.7% |
| VSDeploymentProfile.MAX_ACCURACY | What is the capital of France | 109.47 | 140.16 | 28.0% |
| VSDeploymentProfile.MAX_ACCURACY | How does photosynthesis work | 108.87 | 139.88 | 28.5% |
| VSDeploymentProfile.MAX_ACCURACY | Describe the water cycle | 109.3 | 139.99 | 28.1% |
| VSDeploymentProfile.MAX_ACCURACY | What causes earthquakes | 108.26 | 139.26 | 28.6% |