"""SecurityAccess ($27) seed -> key routine.

.. warning::

   **This is a placeholder, not the real algorithm.** The genuine GEMS
   seed->key transform (used by the T4 before an immobiliser "Security Learn"
   or a coding write) is *not public* — it is the one undocumented GEMS
   operation (see ``memory/research/kline-protocols.md``). We model the
   *shape* of the exchange faithfully (``27 01`` -> seed, ``27 02`` -> key,
   with authentic ``$7F $33`` / ``$7F $35`` refusals) using a deterministic
   toy transform so the client helper and the virtual ECU agree.

Both sides — :class:`~gems_t4.protocol.client.KwpClient.security_access` and
the virtual ECU — call :func:`compute_key`, so as long as they share this
module the handshake round-trips. Swapping in a real algorithm later is a
one-function change.
"""
from __future__ import annotations

__all__ = ["SEED_SIZE", "compute_key"]

#: The seed / key are modelled as 16-bit values (matches the MEMS3 seed size).
SEED_SIZE = 16

#: Bit mask for a :data:`SEED_SIZE`-bit value.
_MASK = (1 << SEED_SIZE) - 1

#: Opaque constants for the toy transform. Arbitrary; not derived from GEMS.
_XOR_CONST = 0x5A3C
_ADD_CONST = 0x1F4B


def compute_key(seed: int) -> int:
    """Derive a 16-bit key from a 16-bit ``seed`` (TOY / placeholder routine).

    The transform is deterministic and reversible-looking but has **no
    cryptographic value and no relationship to the real GEMS algorithm**. It
    exists only so the emulated tester and ECU compute the same key:

    1. mask the seed to 16 bits,
    2. rotate left by 3 bits,
    3. XOR with a constant,
    4. add a constant (mod 2**16).

    Parameters
    ----------
    seed:
        The seed returned by the ECU in the ``27 01`` positive response.

    Returns
    -------
    int
        The 16-bit key to send back in ``27 02``.

    Raises
    ------
    ValueError
        If ``seed`` is negative.
    """
    if seed < 0:
        raise ValueError(f"seed must be non-negative, got {seed}")
    s = seed & _MASK
    rotated = ((s << 3) | (s >> (SEED_SIZE - 3))) & _MASK
    return ((rotated ^ _XOR_CONST) + _ADD_CONST) & _MASK
