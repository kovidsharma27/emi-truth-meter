"""Checks that every page loads and the website shows the same numbers as the guide."""
from app import app
from modes import MODES

client = app.test_client()


def test_home_and_all_pages_load():
    assert client.get("/").status_code == 200
    for key in MODES:
        assert client.get(f"/calc/{key}").status_code == 200
        assert client.get(f"/calc/{key}?example=1").status_code == 200


def test_unknown_page_is_404():
    assert client.get("/calc/nothing").status_code == 404


def test_no_cost_emi_shows_guide_numbers():
    page = client.post("/calc/no-cost-emi", data={
        "price": "30000", "cash_price": "28500", "months": "6", "fee": "199", "gst": "on"}).get_data(as_text=True)
    assert "23.5%" in page and "Very costly" in page and "₹1,969" in page


def test_bad_input_gives_friendly_error():
    page = client.post("/calc/no-cost-emi", data={
        "price": "28000", "cash_price": "28500", "months": "6", "fee": "0"}).get_data(as_text=True)
    assert "cannot be more than" in page
    page = client.post("/calc/flat-rate", data={"principal": "abc", "flat_rate": "8", "months": "36"}).get_data(as_text=True)
    assert "Please enter a number" in page


def test_card_dues_never_ending_payment():
    page = client.post("/calc/card-dues", data={"balance": "20000", "monthly_rate": "3.5", "payment": "500"}).get_data(as_text=True)
    assert "never finish" in page


def test_prepay_and_others_run():
    assert "₹28,062" in client.post("/calc/prepay", data={
    "principal": "500000", "rate": "10", "months": "60", "paid": "0", "extra": "2000", "charge": "0"}).get_data(as_text=True)
    assert "21.5%" in client.post("/calc/flat-rate", data={
    "principal": "100000", "flat_rate": "12", "months": "12", "fee": "0", "other": "0"}).get_data(as_text=True)


# ---------- compare page ----------
def test_compare_loads_and_example():
    assert client.get("/compare").status_code == 200
    page = client.get("/compare?example=1").get_data(as_text=True)
    assert "28500" in page and "30000" in page


def test_compare_emi_vs_cash():
    page = client.post("/compare", data={
        "a_mode": "no-cost-emi", "a_price": "30000", "a_cash_price": "28500", "a_months": "6",
        "a_fee": "199", "a_gst": "on",
        "b_mode": "cash", "b_price": "28500"}).get_data(as_text=True)
    assert "Offer B costs ₹1,969 less in total." in page
    assert "23.5%" in page and "0.0%" in page


def test_compare_two_loans_and_same_total():
    page = client.post("/compare", data={
        "a_mode": "cash", "a_price": "5000", "b_mode": "cash", "b_price": "5000"}).get_data(as_text=True)
    assert "cost the same" in page
    page = client.post("/compare", data={
        "a_mode": "flat-rate", "a_principal": "100000", "a_flat_rate": "8", "a_months": "36", "a_fee": "0", "a_other": "0",
        "b_mode": "normal-loan", "b_principal": "100000", "b_rate": "12", "b_months": "36", "b_fee": "0", "b_other": "0"}).get_data(as_text=True)
    assert "Offer B costs" in page


def test_compare_errors_name_the_offer():
    page = client.post("/compare", data={
        "a_mode": "cash", "a_price": "abc", "b_mode": "cash", "b_price": "100"}).get_data(as_text=True)
    assert "Offer A:" in page and "Please enter a number" in page
    page = client.post("/compare", data={"a_mode": "bogus", "b_mode": "cash", "b_price": "1"}).get_data(as_text=True)
    assert "choose a type of offer" in page

def test_normal_loan_with_fee_and_gst():
    page = client.post("/calc/normal-loan", data={
        "principal": "100000", "rate": "12", "months": "12", "fee": "1000", "gst": "on", "other": "0"}).get_data(as_text=True)
    assert "14.3%" in page and "₹1,07,799" in page and "In plain words" in page


def test_normal_loan_without_charges_matches_quote():
    page = client.post("/calc/normal-loan", data={
        "principal": "100000", "rate": "12", "months": "12", "fee": "0", "other": "0"}).get_data(as_text=True)
    assert "12.0%" in page and "no extra charges" in page

def test_flat_rate_car_example():
    page = client.post("/calc/flat-rate", data={
        "principal": "1000000", "flat_rate": "8", "months": "36", "fee": "0", "other": "0"}).get_data(as_text=True)
    assert "14.5%" in page and "₹12,40,000" in page and "₹2,40,000" in page
    assert "₹80,000 a year" in page and "In plain words" in page

def test_no_cost_emi_plain_words():
    page = client.post("/calc/no-cost-emi", data={
        "price": "30000", "cash_price": "28500", "months": "6", "fee": "199", "gst": "on"}).get_data(as_text=True)
    assert "In plain words" in page and "₹270 GST" in page and "₹30,469" in page and "23.5%" in page


def test_no_cost_emi_genuine_zero_cost():
    page = client.post("/calc/no-cost-emi", data={
        "price": "30000", "cash_price": "30000", "months": "6", "fee": "0"}).get_data(as_text=True)
    assert "genuine zero-cost EMI" in page


def test_zero_percent_with_fee():
    page = client.post("/calc/zero-percent", data={
        "price": "60000", "down_payment": "0", "months": "9", "fee": "1000", "gst": "on",
        "discount_lost": "0"}).get_data(as_text=True)
    assert "4.8%" in page and "₹61,180" in page and "Fair" in page


def test_zero_percent_down_payment_and_error():
    page = client.post("/calc/zero-percent", data={
        "price": "60000", "down_payment": "10000", "months": "8", "fee": "1000", "gst": "on",
        "discount_lost": "3000"}).get_data(as_text=True)
    assert "You pay ₹10,000 on day one" in page
    page = client.post("/calc/zero-percent", data={
        "price": "60000", "down_payment": "60000", "months": "8", "fee": "0",
        "discount_lost": "0"}).get_data(as_text=True)
    assert "must be less than the price" in page

def test_personal_loan_plain_words_and_schedule():
    page = client.post("/calc/personal-loan", data={
        "principal": "200000", "rate": "14", "months": "24", "fee_percent": "2", "gst": "on", "other": "0"}).get_data(as_text=True)
    assert "16.4%" in page and "₹1,95,280" in page and "₹9,603" in page and "₹2,35,182" in page
    assert "In plain words" in page and "How your first months work" in page
    assert "₹2,333" in page and "₹111" in page and "not on the interest" in page


def test_credit_card_emi_plain_words():
    page = client.post("/calc/credit-card-emi", data={
        "price": "50000", "rate": "15", "months": "12", "fee": "499", "gst": "on"}).get_data(as_text=True)
    assert "20.0%" in page and "₹5,492" in page and "₹55,492" in page
    assert "GST is also charged on the interest" in page and "How your first months work" in page

def test_every_loan_page_has_a_month_table():
    normal = client.post("/calc/normal-loan", data={
        "principal": "100000", "rate": "12", "months": "12", "fee": "1000", "gst": "on", "other": "0"}).get_data(as_text=True)
    assert "How your first months work" in normal and "₹1,000" in normal and "₹92,115" in normal

    flat = client.post("/calc/flat-rate", data={
        "principal": "1000000", "flat_rate": "8", "months": "36", "fee": "0", "other": "0"}).get_data(as_text=True)
    assert "₹6,667" in flat and "₹9,72,222" in flat and "every month, even in the last month" in flat

    nocost = client.post("/calc/no-cost-emi", data={
        "price": "30000", "cash_price": "28500", "months": "6", "fee": "199", "gst": "on"}).get_data(as_text=True)
    assert "How your first months work" in nocost and "Start" in nocost and "₹28,301" in nocost and "₹554" in nocost

    zero = client.post("/calc/zero-percent", data={
        "price": "60000", "down_payment": "0", "months": "9", "fee": "1000", "gst": "on",
        "discount_lost": "0"}).get_data(as_text=True)
    assert "₹58,820" in zero and "₹235" in zero


def test_card_dues_story_and_table():
    page = client.post("/calc/card-dues", data={
        "balance": "20000", "monthly_rate": "3.5", "payment": "1000", "gst": "on"}).get_data(as_text=True)
    assert "₹826" in page and "₹174" in page and "44 months" in page
    assert "In plain words" in page and "How your first months work" in page
    assert "Interest + GST" in page and "If you paid ₹2,000 a month instead" in page


def test_prepay_with_emis_paid_and_charge():
    page = client.post("/calc/prepay", data={
        "principal": "500000", "rate": "10", "months": "60", "paid": "12", "extra": "5000", "charge": "2"}).get_data(as_text=True)
    assert "₹4,18,866" in page and "₹30,350" in page and "prepayment" in page
    assert "Owed with extra" in page
    bad = client.post("/calc/prepay", data={
        "principal": "500000", "rate": "10", "months": "60", "paid": "60", "extra": "5000", "charge": "0"}).get_data(as_text=True)
    assert "must be fewer than" in bad

def test_compare_different_months_and_rate_line():
    page = client.post("/compare", data={
        "a_mode": "normal-loan", "a_principal": "100000", "a_rate": "12", "a_months": "12",
        "a_fee": "0", "a_other": "0",
        "b_mode": "normal-loan", "b_principal": "100000", "b_rate": "10", "b_months": "11",
        "b_fee": "0", "b_other": "0"}).get_data(as_text=True)
    assert "12 months (1 yr)" in page and "11 months" in page
    assert "different lengths of time (12 months and 11 months)" in page
    assert "Offer B has the lower real yearly rate (10.0% against 12.0%)" in page
    assert "Offer B costs" in page and "You pay every month (EMI)" in page


def test_compare_page_has_two_offer_cards():
    page = client.get("/compare").get_data(as_text=True)
    assert page.count('class="offer"') == 2 and "What kind of offer is this?" in page
    assert "Pay the full price today by cash, UPI or card" in page

def test_script_is_linked_so_the_offer_menu_works():
    page = client.get("/compare").get_data(as_text=True)
    assert 'static/script.js' in page and "defer" in page
    assert client.get("/static/script.js").status_code == 200

def test_personal_loan_fee_in_percent_gives_helpful_error():
    page = client.post("/calc/personal-loan", data={
        "principal": "200000", "rate": "8", "months": "12", "fee_percent": "200", "gst": "on", "other": "0"}).get_data(as_text=True)
    assert "it is a percentage of the loan" in page and "Other charges" in page