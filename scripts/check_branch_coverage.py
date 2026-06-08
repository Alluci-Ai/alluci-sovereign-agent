#!/usr/bin/env python3
"""Check branch coverage thresholds for backend/security package.

This script parses the generated ``coverage.xml`` (produced by ``pytest --cov=backend``
or ``coverage run -m pytest``) and enforces two tiered branch coverage levels:

* ``backend/security/auth.py``   – 90% minimum branch coverage
* all other files in ``backend/security/`` – 85% minimum branch coverage

The script exits with status 0 when all thresholds are met, otherwise prints a
summary of failures and exits with status 1.  It is intended to be run in CI
(e.g., as a step in a GitHub Actions workflow) or locally after running the test
suite.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

COVERAGE_XML = Path("coverage.xml")
if not COVERAGE_XML.is_file():
    print("Error: coverage.xml not found in the current directory.", file=sys.stderr)
    sys.exit(1)

try:
    tree = ET.parse(COVERAGE_XML)
    root = tree.getroot()
except ET.ParseError as e:
    print(f"Error parsing coverage.xml: {e}", file=sys.stderr)
    sys.exit(1)

failed = []
# Iterate over each <class> element – it holds file‑wise metrics.
for cls in root.findall('.//class'):
    filename = cls.attrib.get('filename', '')
    # Only consider files inside backend/security/.
    if not filename.startswith('backend/security/'):
        continue
    # Branch metrics may be missing if ``branch=False`` for that file.
    branches = int(cls.attrib.get('branches', 0))
    covered = int(cls.attrib.get('coveredbranches', 0))
    if branches == 0:
        # No branch data – treat as a pass (or could be a warning).
        continue
    pct = covered / branches
    # Apply thresholds.
    if filename.endswith('auth.py'):
        required = 0.90
    else:
        required = 0.85
    if pct < required:
        failed.append((filename, covered, branches, pct, required))

if failed:
    print("Branch coverage thresholds not met:")
    for fn, cov, tot, pct, req in failed:
        print(f"  {fn}: {cov}/{tot} ({pct:.0%}) < required {req:.0%}")
    sys.exit(1)
else:
    print("All backend/security branch coverage thresholds satisfied.")
    sys.exit(0)
