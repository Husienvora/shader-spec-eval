# Contributing

Contributions that try to break the grader are especially welcome.

Good issues and pull requests include:

- a valid shader that a property incorrectly rejects;
- an invalid shader that receives full credit;
- a new task isolating one spatial or temporal capability;
- a new positive/negative control;
- renderer differences across platforms;
- repeated model results with complete metadata.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m playwright install chromium
shader-spec-eval selftest
pytest
ruff check .
```

Avoid changing thresholds solely to improve one model's score. Any assertion change must include a
control demonstrating the failure mode it fixes. Keep generated result files out of
`results/latest`; curated reproducible findings may be added under a named `results/` directory.
