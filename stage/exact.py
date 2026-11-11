"""Exact rationals written as text: a decimal when it ends, else n/d -- and back, without loss."""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction as F


def fstr(v: F) -> str:
    """The exact value: a plain decimal if its denominator has no prime but 2 and 5, else 'n/d'."""
    v = F(v)
    d = v.denominator
    k2 = k5 = 0
    while d % 2 == 0:
        d //= 2; k2 += 1
    while d % 5 == 0:
        d //= 5; k5 += 1
    if d != 1:
        return f"{v.numerator}/{v.denominator}"
    places = max(k2, k5)
    q = abs(v.numerator) * 10 ** places // v.denominator
    sign = "-" if v < 0 else ""
    whole, frac = divmod(q, 10 ** places)
    s = f"{sign}{whole}.{frac:0{places}d}" if places else f"{sign}{whole}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def fparse(s: str) -> F:
    if "/" in s:
        a, b = s.split("/")
        return F(int(a), int(b))
    return F(Decimal(s))


def fmt(v: F, places: int = 6) -> str:
    """To `places` decimals, rounded half away from zero -- as REVOTT STAMPS writes a TNLDY."""
    q = abs(F(v)) * 10 ** places
    n = int(q) + (1 if q - int(q) >= F(1, 2) else 0)
    sign = "-" if v < 0 and n else ""
    whole, frac = divmod(n, 10 ** places)
    return f"{sign}{whole}.{frac:0{places}d}" if places else f"{sign}{whole}"
