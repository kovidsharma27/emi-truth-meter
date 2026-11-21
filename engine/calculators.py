"""EMI Truth Meter - calculation engine.

Every function takes plain numbers and returns a dictionary, so the web
page (and the tests) can use the results directly.
Rates are yearly percentages (12 means 12%). Money is in rupees.
"""

GST = 18  # percent, charged on interest and on fees


# ---------- basic building blocks ----------

def emi(principal, yearly_rate, months):
    """Fixed monthly instalment for a normal (reducing balance) loan."""
    r = yearly_rate / 12 / 100
    if r == 0:
        return principal / months
    return principal * r * (1 + r) ** months / ((1 + r) ** months - 1)


def real_rate(received, payments):
    """Find the real yearly rate (in %) by guessing 'higher or lower'.

    received : money that actually reached you (or its value) today
    payments : list of amounts paid at the end of month 1, 2, 3, ...
    """
    low, high = 0.0, 1.0                 # monthly rate between 0% and 100%
    for _ in range(100):
        mid = (low + high) / 2           # our guess
        worth = sum(p / (1 + mid) ** (i + 1) for i, p in enumerate(payments))
        if worth > received:             # guess too low, go higher
            low = mid
        else:                            # guess too high, go lower
            high = mid
    return mid * 12 * 100


def verdict(rate):
    """Our simple guide: up to 10% fair, 10-18% costly, above 18% very costly."""
    if rate <= 10:
        return "Fair"
    if rate <= 18:
        return "Costly"
    return "Very costly"


def _result(received, payments, extra_paid, **more):
    rate = real_rate(received, payments)
    out = {"received": received, "extra_paid": extra_paid,
           "real_rate": rate, "verdict": verdict(rate)}
    out.update(more)
    return out


# ---------- the 7 modes ----------

def normal_loan(principal, yearly_rate, months, fee=0):
    """Mode 1: ordinary bank loan. fee = processing fee in rupees (optional)."""
    e = emi(principal, yearly_rate, months)
    interest = e * months - principal
    return _result(principal - fee, [e] * months, interest + fee,
                   emi=e, total_interest=interest)


def flat_loan(principal, flat_rate, months):
    """Mode 2: flat-rate loan. Interest is on the full amount for the full time."""
    interest = principal * flat_rate / 100 * (months / 12)
    e = (principal + interest) / months
    return _result(principal, [e] * months, interest,
                   emi=e, total_interest=interest)


def no_cost_emi(price, cash_price, months, fee=0, gst_on_interest=True):
    """Mode 3: No-Cost EMI.
    price      = price on EMI (what the EMIs add up to)
    cash_price = price if you paid cash (after the discount)
    """
    hidden_interest = price - cash_price           # the discount you lose
    gst = hidden_interest * GST / 100 if gst_on_interest else 0
    e = (price + gst) / months
    total = e * months + fee
    return _result(cash_price - fee, [e] * months, total - cash_price,
                   emi=e, hidden_interest=hidden_interest, gst=gst, total_paid=total)


def zero_percent_emi(price, months, fee=0, gst_on_fee=True, discount_lost=0):
    """Mode 4: 0% EMI where the only cost is a processing fee."""
    fee_total = fee * (1 + GST / 100) if gst_on_fee else fee
    e = price / months
    received = price - discount_lost - fee_total
    return _result(received, [e] * months, price + fee_total - (price - discount_lost),
                   emi=e, fee_total=fee_total)


def card_emi(price, yearly_rate, months, fee=0, gst_on_fee=True):
    """Mode 5: credit card EMI. GST is added on the interest part of every EMI."""
    e = emi(price, yearly_rate, months)
    r = yearly_rate / 1200
    balance, payments, gst_total = price, [], 0
    for _ in range(months):
        interest = balance * r
        balance -= e - interest
        gst = interest * GST / 100
        payments.append(e + gst)
        gst_total += gst
    fee_total = fee * (1 + GST / 100) if gst_on_fee else fee
    extra = sum(payments) + fee_total - price
    return _result(price - fee_total, payments, extra,
                   emi=e, total_interest=e * months - price,
                   gst_total=gst_total, fee_total=fee_total)


def personal_loan(principal, yearly_rate, months, fee_percent=0, gst_on_fee=True):
    """Mode 6: personal loan. The fee is cut BEFORE the money reaches you."""
    fee = principal * fee_percent / 100
    fee_total = fee * (1 + GST / 100) if gst_on_fee else fee
    e = emi(principal, yearly_rate, months)
    interest = e * months - principal
    return _result(principal - fee_total, [e] * months, interest + fee_total,
                   emi=e, total_interest=interest, fee_total=fee_total)


def card_dues(balance, monthly_rate, payment):
    """Mode 7: unpaid credit card balance. monthly_rate in % per month."""
    months, interest_total = 0, 0.0
    if payment <= balance * monthly_rate / 100:
        return {"possible": False}        # payment never covers the interest
    while balance > 0.01:
        interest = balance * monthly_rate / 100
        interest_total += interest
        balance += interest - min(payment, balance + interest)
        months += 1
    return {"possible": True, "months": months, "total_interest": interest_total,
            "yearly_rate_simple": monthly_rate * 12,
            "yearly_rate_compounded": ((1 + monthly_rate / 100) ** 12 - 1) * 100}


def prepay(principal, yearly_rate, months, extra):
    """Bonus: how much time and interest you save by paying 'extra' each month."""
    e = emi(principal, yearly_rate, months)

    def run(extra_amount):
        bal, m, total_interest = principal, 0, 0.0
        while bal > 0.01:
            i = bal * yearly_rate / 1200
            total_interest += i
            bal += i - min(e + extra_amount, bal + i)
            m += 1
        return m, total_interest

    m0, i0 = run(0)
    m1, i1 = run(extra)
    return {"emi": e, "months_normal": m0, "months_with_extra": m1,
            "interest_normal": i0, "interest_with_extra": i1,
            "interest_saved": i0 - i1, "months_saved": m0 - m1}