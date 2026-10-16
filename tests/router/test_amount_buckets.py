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


def test_trailing_minor_unit_column_folds_into_the_amount() -> None:
    out, count = bucket_amounts("balance <AMT:~1e7> 99 payable")
    assert out == "balance <AMT:~1e7> payable"
    assert count == 1
    cent, n = bucket_amounts("note ¢ column <AMT:~1e6> 75 settled")
    assert cent == "note ¢ column <AMT:~1e6> settled"
    assert n == 1
    raw, n2 = bucket_amounts("AED 8,765,432 75 only")
    assert raw == "AED <AMT:~1e6> only"
    assert n2 == 2


def test_hundredths_tail_folds_into_the_preceding_amount() -> None:
    out, count = bucket_amounts("net <AMT:~1e5> and 99/100 fils due")
    assert out == "net <AMT:~1e5> due"
    assert count == 1
    raw, n = bucket_amounts("USD 3,250.00 and 05/100 cents flat")
    assert raw == "USD <AMT:~1e3> flat"
    assert n == 2
    halala, n2 = bucket_amounts("fee <AMT:~1e4> and 25/100 halalas net")
    assert halala == "fee <AMT:~1e4> net"
    assert n2 == 1


def test_slash_coded_references_become_one_token() -> None:
    out, count = bucket_amounts(
        "see QX/48/2031/77/6 and KLM/12/8704/63 and lot AB12/CD34."
    )
    assert out == "see <REF> and <REF> and lot <REF>."
    assert count == 3
    coded, n = bucket_amounts("ticket AB/4821 closed")
    assert coded == "ticket <REF> closed"
    assert n == 1
    blanks, n2 = bucket_amounts("form __/8/120/44/3 attached")
    assert blanks == "form <REF> attached"
    assert n2 == 1


def test_dates_percentages_fractions_and_existing_tokens_stay() -> None:
    text = (
        "On 05/07/2023 and 2023/07/05 and 12-Apr-17 VAT was 15% "
        "of page 1/2. ratio <AMT:~1e3> 9.9 and part <AMT:~1e2> 9/12. "
        "keep <AMT:~1e6> 99 beside ███."
    )
    out, count = bucket_amounts(text)
    assert "05/07/2023" in out
    assert "2023/07/05" in out
    assert "12-Apr-17" in out
    assert "15%" in out
    assert "1/2" in out
    assert "<AMT:~1e3> 9.9" in out
    assert "<AMT:~1e2> 9/12" in out
    assert "███" in out
    assert "<AMT:~1e6>" in out
    assert "99" not in out
    assert count == 1


def test_spaced_thousands_groups_become_magnitude_tokens() -> None:
    cases = (
        ("8 765 432", "<AMT:~1e6>"),
        ("AED 8 765 432", "AED <AMT:~1e6>"),
        ("1\u00a0250\u00a0000", "<AMT:~1e6>"),
        ("1\u2009250\u2009000", "<AMT:~1e6>"),
        ("1\u202f250\u202f000", "<AMT:~1e6>"),
        ("1 250 000.00", "<AMT:~1e6>"),
        ("12 500.50", "<AMT:~1e4>"),
    )
    for raw, token in cases:
        out, count = bucket_amounts(raw)
        assert out == token, raw
        assert count == 1, raw


def test_spaced_thousands_groups_are_idempotent() -> None:
    text = "8 765 432 then AED 8 765 432 then 1\u00a0250\u00a0000 then 1 250 000.00 then 12 500.50"
    once, first = bucket_amounts(text)
    twice, second = bucket_amounts(once)
    assert once == (
        "<AMT:~1e6> then AED <AMT:~1e6> then <AMT:~1e6> then <AMT:~1e6> then <AMT:~1e4>"
    )
    assert first == 5
    assert twice == once
    assert second == 0


def test_unlabelled_comma_thousands_fold() -> None:
    """One comma group of three is an amount. No second group and no label."""
    cases = (
        ("1,250", "<AMT:~1e3>"),
        ("12,500", "<AMT:~1e4>"),
        ("see 1,250 today", "see <AMT:~1e3> today"),
        ("pay 12,500 now", "pay <AMT:~1e4> now"),
        ("amount 1,250", "amount <AMT:~1e3>"),
        ("total: 12,500", "total: <AMT:~1e4>"),
        ("1,250 AED", "<AMT:~1e3> AED"),
        ("AED 12,500", "AED <AMT:~1e4>"),
        ("1,250.00", "<AMT:~1e3>"),
        ("12,500.50", "<AMT:~1e4>"),
        ("1,234,567.89", "<AMT:~1e6>"),
    )
    for raw, token in cases:
        out, count = bucket_amounts(raw)
        assert out == token, raw
        assert count == 1, raw


def test_mixed_separators_stay_untokenised() -> None:
    samples = (
        "1,234 567",
        "1 234,567",
        "1, 234,567",
        "1,234, 567",
        "123,456 789",
        "123 456,789",
        "1,234 567,890",
        "1 234,567,890",
        "AED 1,234 567",
        "1,234 567 AED",
        "12,500 000",
        "1,234 567.89",
        "1 234,567.89",
    )
    for raw in samples:
        out, count = bucket_amounts(raw)
        assert out == raw, raw
        assert count == 0, raw


def test_comma_groups_keep_exclusions_and_space_groups() -> None:
    stayed = (
        "1 250",
        "12 500",
        "1,250 kg",
        "12,500 m2",
        "1,250%",
        "1,250 days",
        "+971 50 123 4567",
    )
    for raw in stayed:
        out, count = bucket_amounts(raw)
        assert out == raw, raw
        assert count == 0, raw
    spaced, n = bucket_amounts("8 765 432 then 1 250 000.00 then 12 500.50")
    assert spaced == "<AMT:~1e6> then <AMT:~1e6> then <AMT:~1e4>"
    assert n == 3


def test_comma_and_mixed_groups_second_pass_is_idempotent() -> None:
    text = (
        "1,250 then 12,500 then 1,234,567.89 then amount 12,500 "
        "then 8 765 432 then 1,234 567 then 123 456,789"
    )
    once, first = bucket_amounts(text)
    twice, second = bucket_amounts(once)
    assert once == (
        "<AMT:~1e3> then <AMT:~1e4> then <AMT:~1e6> then amount <AMT:~1e4> "
        "then <AMT:~1e6> then 1,234 567 then 123 456,789"
    )
    assert first == 5
    assert twice == once
    assert second == 0


def test_bucket_amounts_second_pass_is_idempotent() -> None:
    text = "pay <AMT:~1e6> 99 and 45/100 fils under ZX/10/2030/44/1 today"
    once, first = bucket_amounts(text)
    twice, second = bucket_amounts(once)
    assert once == "pay <AMT:~1e6> under <REF> today"
    assert first == 3
    assert twice == once
    assert second == 0
