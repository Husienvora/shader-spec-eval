# Exploratory Qwen2.5-Coder 14B run

This is the first local pilot, not a comparative leaderboard result.

- Model: `qwen2.5-coder:14b` through Ollama
- Parameters/quantization: 14.8B, Q4_K_M
- Ollama: 0.32.15
- Python: 3.13.14
- GPU/driver: NVIDIA GeForce RTX 4070 Ti SUPER, 610.88
- Temperature: `0.7`
- Seeds: `7`, `8`, `9`
- Tasks: five
- Generated shaders: 15
- Compiled: 15/15
- Mean property compliance: 87.84%
- Clean completions: 5/15
- Full-ladder repeat scores: 86.84%, 85.09%, 91.59%
- Within-model standard deviation: 3.36 percentage points

Open `shader-dashboard.html` locally to inspect every render, generated source file, and property
verdict. `shader-cells.json` is the machine-readable source of truth.
