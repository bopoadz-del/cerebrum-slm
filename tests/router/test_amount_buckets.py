"""Magnitude buckets for amounts written in words or as exact digits.

Synthetic strings only. Ingest rows are checked in test_slm_ingest_1015.
"""

from router.amount_buckets import bucket_amounts, magnitude_token


def test_written_amounts_become_magnitude_tokens() -> None:
    cases = (
        ("one hundred", "<AMT:~1e2>"),
        ("fifty thousand", "<AMT:~1e4>"),
        ("one hundred and twenty", "<AMT:~1e2>"),
        ("nine million one hundred ninety eight thousand two hundred ten", "<AMT:~1e6>"),
        ("forty three million, six hundred and fifty two thousand", "<AMT:~1e7>"),
        ("twenty-one", "<AMT:~1e1>"),
        ("eighty nine", "<AMT:~1e1>"),
    )
    for raw, token in cases:
        out, count = bucket_amounts(f"the sum of {raw} dirhams")
        assert out == f"the sum of {token} dirhams", raw
        assert count == 1


def test_fils_fraction_is_part_of_the_written_amount() -> None:
    out, count = bucket_amounts(
        "Dirhams nine million one hundred and fils 56/100 only"
    )
    assert out == "Dirhams <AMT:~1e6> only"
    assert count == 1
    assert "56" not in out


def test_exact_digit_amounts_become_magnitude_tokens() -> None:
    out, count = bucket_amounts("AED 1,234,567.89 then 866.60 and 0.00")
    assert out == "AED <AMT:~1e6> then <AMT:~1e2> and <AMT:~1e0>"
    assert count == 3
    spaced, n = bucket_amounts("price AED 612, 801, 84.00 today")
    assert spaced == "price AED <AMT:~1e7> today"
    assert n == 1


def test_dates_clauses_percentages_and_small_counts_stay() -> None:
    text = (
        "Sub-Clause 14.3 on 05.07.2023 and 30 June 2023. "
        "VAT 5% over 120 days. Application No. 36. one window."
    )
    out, count = bucket_amounts(text)
    assert out == text
    assert count == 0


def test_existing_magnitude_tokens_are_stable() -> None:
    text = "net AED <AMT:~1e6> (<AMT:~1e4>)"
    out, count = bucket_amounts(text)
    assert out == text
    assert count == 0
    again, count2 = bucket_amounts(out)
    assert again == out and count2 == 0


def test_zero_and_fraction_exponents() -> None:
    assert magnitude_token(0) == "<AMT:~1e0>"
    assert magnitude_token(0.56) == "<AMT:~1e-1>"
    assert magnitude_token(100) == "<AMT:~1e2>"
