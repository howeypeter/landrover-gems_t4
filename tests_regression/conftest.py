"""Shared setup for the independent v0.0.4 regression suite.

This suite was written from scratch against the frozen contracts
(INTERFACES.md, GUI_INTERFACES.md) and the user-facing docs — deliberately
NOT derived from the original ``tests/`` suite — so it provides an
independent check that the code does what the documentation promises.

Run it explicitly (it is outside pyproject's ``testpaths``):

    .venv\\Scripts\\python.exe -m pytest tests_regression -q
"""
import os

# GUI tests must never open a real window or sit in the simulated
# "Communicating with ECU" waits (same knobs the docs describe for CI).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("GEMS_T4_INSTANT", "1")
