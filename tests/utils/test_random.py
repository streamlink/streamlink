from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Sequence
from itertools import count

import pytest

from streamlink.utils.random import (
    CHOICES_ALPHA,
    CHOICES_ALPHA_LOWER,
    CHOICES_ALPHA_NUM,
    CHOICES_ALPHA_UPPER,
    CHOICES_HEX_LOWER,
    CHOICES_HEX_UPPER,
    CHOICES_NUM,
    random_token,
)


@pytest.fixture()
def _iterated_choice(monkeypatch: pytest.MonkeyPatch):
    choices: dict[Sequence, Iterator[int]] = defaultdict(count)

    def fake_choice(seq):
        return seq[next(choices[seq]) % len(seq)]

    monkeypatch.setattr("streamlink.utils.random.choice", fake_choice)


@pytest.mark.usefixtures("_iterated_choice")
@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (
            dict(),
            "0123456789abcdefghijklmnopqrstuv",
        ),
        (
            dict(length=62),
            "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        ),
        (
            dict(length=20, choices=CHOICES_NUM),
            "01234567890123456789",
        ),
        (
            dict(length=52, choices=CHOICES_ALPHA_LOWER),
            "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz",
        ),
        (
            dict(length=52, choices=CHOICES_ALPHA_UPPER),
            "ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZ",
        ),
        (
            dict(length=104, choices=CHOICES_ALPHA),
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        ),
        (
            dict(length=100, choices=CHOICES_ALPHA_NUM),
            "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyzAB",
        ),
        (
            dict(length=32, choices=CHOICES_HEX_LOWER),
            "0123456789abcdef0123456789abcdef",
        ),
        (
            dict(length=32, choices=CHOICES_HEX_UPPER),
            "0123456789ABCDEF0123456789ABCDEF",
        ),
    ],
)
def test_random_token(args, expected):
    assert random_token(**args) == expected
