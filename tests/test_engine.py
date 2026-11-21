"""Tests: every number below comes from the worked examples in the project guide."""
from pytest import approx
from engine.calculators import *


def test_emi_basic():
    assert emi(100000, 12, 12) == approx(8884.88, abs=0.01)


def test_mode1_normal_loan():
    r = normal_loan(100000, 12, 12)
    assert r["total_interest"] == approx(6618.55, abs=0.01)
    assert r["real_rate"] == approx(12.0, abs=0.01)


def test_mode2_flat_loan():
    assert flat_loan(100000, 12, 12)["real_rate"] == approx(21.5, abs=0.1)
    assert flat_loan(100000, 8, 36)["real_rate"] == approx(14.5, abs=0.1)
    assert flat_loan(300000, 10, 60)["real_rate"] == approx(17.3, abs=0.1)


def test_mode3_no_cost_emi():
    assert no_cost_emi(30000, 28500, 6, fee=0, gst_on_interest=False)["real_rate"] == approx(17.8, abs=0.1)
    assert no_cost_emi(30000, 28500, 6, fee=0)["real_rate"] == approx(21.0, abs=0.1)
    r = no_cost_emi(30000, 28500, 6, fee=199)
    assert r["real_rate"] == approx(23.5, abs=0.1)
    assert r["extra_paid"] == approx(1969, abs=0.5)
    assert r["verdict"] == "Very costly"


def test_mode4_zero_percent():
    assert zero_percent_emi(60000, 9, fee=1000)["real_rate"] == approx(4.8, abs=0.1)
    assert zero_percent_emi(60000, 9, fee=1000, discount_lost=3000)["real_rate"] == approx(17.6, abs=0.1)


def test_mode5_card_emi():
    r = card_emi(50000, 15, 12, fee=499)
    assert r["real_rate"] == approx(20.0, abs=0.1)
    assert r["extra_paid"] == approx(5492, abs=1)


def test_mode6_personal_loan():
    r = personal_loan(200000, 14, 24, fee_percent=2)
    assert r["received"] == approx(195280, abs=0.5)
    assert r["real_rate"] == approx(16.4, abs=0.1)


def test_mode7_card_dues():
    a = card_dues(20000, 3.5, 1000)
    b = card_dues(20000, 3.5, 2000)
    assert a["months"] > b["months"] and a["total_interest"] > 2 * b["total_interest"]
    assert card_dues(20000, 3.5, 500)["possible"] is False


def test_prepay():
    r = prepay(500000, 10, 60, 2000)
    assert r["months_with_extra"] == 49
    assert r["interest_saved"] == approx(28062, abs=2)
