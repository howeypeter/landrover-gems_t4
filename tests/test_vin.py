"""VIN decode / check-digit / reconstruction helpers (gems_t4.gems.vin).

Test vectors are the ones documented in docs/vin-decode.md §3 (from Wikibooks).
"""
from __future__ import annotations

import pytest

from gems_t4.gems import vin


# --- check digit (the documented vectors) ----------------------------------- #

def test_check_digit_wikibooks_example():
    # 1M8GDM9A_KP042788 -> transliterated·weighted sum 351, 351 % 11 == 10 -> X
    assert vin.check_digit("1M8GDM9AXKP042788") == "X"
    # position 9 is ignored, so a wrong char there gives the same answer
    assert vin.check_digit("1M8GDM9A0KP042788") == "X"


def test_check_digit_all_ones_is_valid():
    # Seventeen 1s is a valid VIN (its own check digit is 1).
    assert vin.check_digit("11111111111111111") == "1"
    assert vin.validate_vin("11111111111111111")


def test_validate_vin_true_and_false():
    assert vin.validate_vin("1M8GDM9AXKP042788")
    # flip the check digit -> invalid
    assert not vin.validate_vin("1M8GDM9A1KP042788")


def test_check_digit_rejects_bad_length_and_chars():
    with pytest.raises(ValueError):
        vin.check_digit("TOOSHORT")
    with pytest.raises(ValueError):
        vin.check_digit("1M8GDM9AXKP04278Q")  # Q is never a valid VIN char
    # validate_vin swallows the errors and just returns False
    assert not vin.validate_vin("TOOSHORT")
    assert not vin.validate_vin("1M8GDM9AXKP04278Q")


# --- model year (position 10, 30-year cycle) -------------------------------- #

def test_model_year_base_and_gems_window():
    assert vin.model_year("T") == 1996
    assert vin.model_year("V") == 1997
    assert vin.model_year("W") == 1998
    assert vin.model_year("X") == 1999


def test_model_year_era_hint_disambiguates_cycle():
    # T is 1996 or 2026; the hint picks the nearer.
    assert vin.model_year("T", era=2025) == 2026
    assert vin.model_year("T", era=1997) == 1996


def test_model_year_rejects_unused_codes():
    for bad in ("U", "Z", "0", "I", "O", "Q"):
        with pytest.raises(ValueError):
            vin.model_year(bad)


# --- reconstruction (the whole point) --------------------------------------- #

def test_reconstruct_nas_disco1_gems_is_self_consistent():
    # Federal NAS Disco-1 GEMS 4.0 auto, 1997, Solihull, serial 123456.
    full = vin.reconstruct_vin("SALJY124", "V", "123456", plant="A")
    assert len(full) == 17
    assert full.startswith("SALJY124")   # pos 1-8 fixed stem
    assert full[9] == "V"                # year in pos 10
    assert full[10] == "A"               # plant in pos 11
    assert full.endswith("123456")       # serial
    # the computed check digit makes it validate
    assert vin.validate_vin(full)


def test_reconstruct_matches_decode_round_trip():
    full = vin.reconstruct_vin("SALJY124", "T", "A99999", plant="A")
    d = vin.decode_vin(full)
    assert d.wmi == "SAL"
    assert d.model_line == "Discovery"
    assert d.body == "4-door wagon"
    assert d.engine == "3.9/4.0L V8"
    assert d.transmission == "ZF 4-sp auto (LHD)"
    assert d.year == 1996
    assert d.plant == "Solihull, UK"
    assert d.serial == "A99999"
    assert d.check_digit_ok


def test_reconstruct_rejects_bad_lengths():
    with pytest.raises(ValueError):
        vin.reconstruct_vin("SALJY12", "V", "123456")   # 7-char prefix
    with pytest.raises(ValueError):
        vin.reconstruct_vin("SALJY124", "V", "12345")   # 5-char serial
    with pytest.raises(ValueError):
        vin.reconstruct_vin("SALJY124", "VV", "123456")  # 2-char year
