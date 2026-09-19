"""VIN decode, check-digit, and reconstruction from the ECU/10AS last-6.

Pure helpers, no I/O. Two Land Rover VIN schemes exist and are *structurally
different* (see ``docs/vin-decode.md``):

* **NAS** (US/Canada, 1987-): single-char model line at pos 4, series/emissions
  at 5, body 6, engine 7, transmission 8, a **check digit at pos 9**, year 10,
  plant 11, serial 12-17. This is the user's Discovery 1 GEMS truck.
* **ROW / UK**: two-letter model/body codes, gearbox at 9, and **no check digit**.

The point of the module: the ECU (or, on a Disco 1, the Lucas 10AS) stores only
the VIN **last-6**; for a known vehicle the first 11 chars are fixed/derivable,
so ``reconstruct_vin(...)`` assembles the full 17-char VIN and (for NAS) computes
the self-validating check digit. Always treat a reconstruction as an
identification aid to be verified against the physical plate, never as proof.
"""
from __future__ import annotations

from dataclasses import dataclass

# --- check digit (NAS position 9; ISO 3779 / 49 CFR 565) --------------------- #

#: Letter -> numeric value for the check-digit sum. I/O/Q are never valid in a
#: VIN, so they are absent; digits map to themselves.
_TRANSLIT: dict[str, int] = {
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "J": 1, "K": 2, "L": 3, "M": 4, "N": 5, "P": 7, "R": 9,
    "S": 2, "T": 3, "U": 4, "V": 5, "W": 6, "X": 7, "Y": 8, "Z": 9,
}

#: Positional weights, left to right (pos 1..17). Pos 9 is weight 0 (it's the
#: check digit itself, so it cancels out).
_WEIGHTS: tuple[int, ...] = (8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2)


def _value(ch: str) -> int:
    ch = ch.upper()
    if ch.isdigit():
        return int(ch)
    try:
        return _TRANSLIT[ch]
    except KeyError as exc:  # I/O/Q or any non-VIN character
        raise ValueError(f"invalid VIN character {ch!r}") from exc


def check_digit(vin: str) -> str:
    """Return the computed NAS check digit for a 17-char VIN.

    The character currently at position 9 is ignored (its weight is 0). Returns
    ``"0".."9"`` or ``"X"`` (when the remainder is 10).
    """
    vin = vin.strip().upper()
    if len(vin) != 17:
        raise ValueError(f"VIN must be 17 characters, got {len(vin)}")
    total = sum(_value(ch) * w for ch, w in zip(vin, _WEIGHTS))
    rem = total % 11
    return "X" if rem == 10 else str(rem)


def validate_vin(vin: str) -> bool:
    """True if the VIN's position-9 check digit matches (NAS scheme only).

    ROW/UK VINs carry no check digit, so this is meaningless for them — call it
    only when you know the VIN is NAS.
    """
    vin = vin.strip().upper()
    if len(vin) != 17:
        return False
    try:
        return vin[8] == check_digit(vin)
    except ValueError:
        return False


# --- model year (NAS position 10) ------------------------------------------- #

#: Year code -> the base (20th-century) year. The code repeats on a 30-year
#: cycle, so each also stands for base+30 (T = 1996 or 2026). U/Z/0 are unused.
_YEAR_BASE: dict[str, int] = {
    "A": 1980, "B": 1981, "C": 1982, "D": 1983, "E": 1984, "F": 1985,
    "G": 1986, "H": 1987, "J": 1988, "K": 1989, "L": 1990, "M": 1991,
    "N": 1992, "P": 1993, "R": 1994, "S": 1995, "T": 1996, "V": 1997,
    "W": 1998, "X": 1999, "Y": 2000,
    "1": 2001, "2": 2002, "3": 2003, "4": 2004, "5": 2005,
    "6": 2006, "7": 2007, "8": 2008, "9": 2009,
}


def model_year(code: str, era: int | None = None) -> int:
    """Decode a position-10 year code to a calendar year.

    The code is ambiguous across a 30-year cycle (``T`` = 1996 or 2026). ``era``
    is a hint year near the expected build; the candidate closest to it wins.
    With no hint, the base (earliest, 20th-century) year is returned — correct
    for GEMS-era Land Rovers (1996-1999).
    """
    code = code.strip().upper()
    try:
        base = _YEAR_BASE[code]
    except KeyError as exc:
        raise ValueError(f"invalid model-year code {code!r}") from exc
    if era is None:
        return base
    candidates = [base, base + 30, base + 60]
    return min(candidates, key=lambda y: abs(y - era))


# --- NAS field decode (GEMS-era subset) ------------------------------------- #

_NAS_MODEL_LINE = {
    "D": "Defender", "H": "Range Rover Classic", "J": "Discovery",
    "P": "Range Rover (P38A)", "T": "Discovery Series II",
}
_NAS_BODY = {"1": "4-door wagon", "2": "2-door soft top / wagon",
             "3": "2-door wagon"}
#: Rover-V8 engine codes (pos 7) for the GEMS era.
_NAS_ENGINE = {
    "1": "3.5L V8", "2": "3.9/4.0L V8", "3": "4.2L V8", "4": "4.6L V8",
    "5": "4.0L V8 (LEV)", "6": "4.6L V8 (LEV/ULEV)", "9": "4.6L V8",
}
_NAS_TRANS = {"4": "ZF 4-sp auto (LHD)", "8": "5-sp manual (LHD)",
              "2": "5-sp auto (Freelander)"}
_PLANT = {"A": "Solihull, UK", "H": "Halewood, UK", "2": "Nitra, Slovakia",
          "F": "worldwide", "G": "South Africa"}


@dataclass(frozen=True, slots=True)
class VinDecode:
    """A decoded VIN. Fields are best-effort; unknown codes pass through raw."""

    vin: str
    wmi: str
    model_line: str
    body: str
    engine: str
    transmission: str
    year: int | None
    plant: str
    serial: str
    check_digit_ok: bool


def decode_vin(vin: str, era: int | None = None) -> VinDecode:
    """Decode a 17-char **NAS** VIN into its GEMS-era fields (best-effort).

    ROW/UK VINs use a different layout (see ``docs/vin-decode.md`` §2) and are
    not handled here. ``era`` disambiguates the model year (see
    :func:`model_year`); it defaults to the GEMS window when the year decodes to
    1996-1999 anyway.
    """
    vin = vin.strip().upper()
    if len(vin) != 17:
        raise ValueError(f"VIN must be 17 characters, got {len(vin)}")
    try:
        year: int | None = model_year(vin[9], era)
    except ValueError:
        year = None
    return VinDecode(
        vin=vin,
        wmi=vin[:3],
        model_line=_NAS_MODEL_LINE.get(vin[3], f"?({vin[3]})"),
        body=_NAS_BODY.get(vin[5], f"?({vin[5]})"),
        engine=_NAS_ENGINE.get(vin[6], f"?({vin[6]})"),
        transmission=_NAS_TRANS.get(vin[7], f"?({vin[7]})"),
        year=year,
        plant=_PLANT.get(vin[10], f"?({vin[10]})"),
        serial=vin[11:],
        check_digit_ok=validate_vin(vin),
    )


def reconstruct_vin(prefix8: str, year_code: str, last6: str, *,
                    plant: str = "A") -> str:
    """Assemble a full 17-char NAS VIN from the known parts + the read serial.

    ``prefix8`` is positions 1-8 (e.g. ``"SALJY124"`` for a federal Disco-1 GEMS
    4.0 auto), ``year_code`` is the position-10 code, ``last6`` is the serial
    read from the ECU/10AS, and ``plant`` is position 11. Position 9 (the check
    digit) is **computed**. The result is an identification aid — verify it
    against the physical plate before trusting it.
    """
    prefix8 = prefix8.strip().upper()
    year_code = year_code.strip().upper()
    last6 = last6.strip().upper()
    if len(prefix8) != 8:
        raise ValueError(f"prefix8 must be 8 chars (pos 1-8), got {len(prefix8)}")
    if len(year_code) != 1:
        raise ValueError("year_code must be a single char (pos 10)")
    if len(plant) != 1:
        raise ValueError("plant must be a single char (pos 11)")
    if len(last6) != 6:
        raise ValueError(f"last6 must be 6 chars (pos 12-17), got {len(last6)}")
    # Build with a placeholder at pos 9, compute the real check digit, splice.
    provisional = f"{prefix8}0{year_code}{plant}{last6}"
    return f"{prefix8}{check_digit(provisional)}{year_code}{plant}{last6}"
