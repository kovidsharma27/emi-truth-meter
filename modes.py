"""Describes each offer type: its form fields, how to run it, how to show it."""
from engine.calculators import (normal_loan, flat_loan, no_cost_emi,
                                card_emi, verdict, emi, real_rate)


# ---------- small helpers ----------
def inr(x):
    """Indian style rupees: 1234567 -> ₹12,34,567"""
    x = int(round(x))
    s = str(abs(x))
    if len(s) > 3:
        head, tail, parts = s[:-3], s[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if x < 0 else "") + "₹" + s


def pct(x):
    return f"{x:.1f}%"


def months_text(m):
    if m == 1:
        return "1 month"
    y, mo = divmod(m, 12)
    if y and mo:
        return f"{m} months ({y} yr {mo} mo)"
    if y:
        return f"{m} months ({y} yr)"
    return f"{m} months"


def schedule(P, yearly_rate, months):
    """Month-by-month split of a normal loan: the EMI and a (interest, repaid, still owed) row per month."""
    e = emi(P, yearly_rate, months)
    r = yearly_rate / 1200
    bal, rows = P, []
    for _ in range(months):
        interest = bal * r
        repaid = e - interest
        bal -= repaid
        rows.append((interest, repaid, max(bal, 0.0)))
    return e, rows


SCHEDULE_HEADERS = ["Month", "Interest", "Loan repaid", "Still owed"]
REDUCING_NOTE = ("The EMI stays the same every month. But the interest is charged only on what you "
                 "still owe, so the interest part shrinks and the loan-repaid part grows.")


def table_view(headers, rows, note, start=None):
    """Keeps a start row (if any), months 1-3, '...', and the last month, so long tables stay short."""
    n = len(rows)
    out = [start] if start else []
    out += rows[:3]
    if n > 4:
        out.append(tuple("..." for _ in headers))
    if n > 3:
        out.append(rows[-1])
    return {"headers": headers, "rows": out, "note": note.strip()}


def schedule_view(rows, extra_note="", note=None, start=None):
    """rows = (interest, repaid, still owed) for each month."""
    text = [(str(k + 1), inr(i), inr(p), inr(b)) for k, (i, p, b) in enumerate(rows)]
    return table_view(SCHEDULE_HEADERS, text, (note or REDUCING_NOTE) + " " + extra_note, start)


def true_rows(received, payments, real_yearly_rate):
    """Splits each payment into interest and loan repaid, using the REAL rate on what you effectively borrowed."""
    r = real_yearly_rate / 1200
    bal, rows = received, []
    for pay in payments:
        interest = bal * r
        bal -= pay - interest
        rows.append((interest, pay - interest, max(bal, 0.0)))
    return rows


def flat_rows(P, rate, months):
    """Flat loan: the interest is the same every month, whatever you still owe."""
    interest, repaid, bal, rows = P * rate / 1200, P / months, P, []
    for _ in range(months):
        bal -= repaid
        rows.append((interest, repaid, max(bal, 0.0)))
    return rows


def advice(verdict_text, extra):
    """One plain sentence telling the user what the verdict means for them."""
    if verdict_text == "Fair":
        return "That is low, and a fair price for paying over time."
    return f"That is {verdict_text.lower()}. If you can pay in full today, you save {inr(extra)}."


def num(name, label, hint="", example="", default=""):
    return {"name": name, "label": label, "hint": hint, "example": example,
            "default": default, "kind": "number"}


def check(name, label, default=True):
    return {"name": name, "label": label, "default": default, "kind": "check",
            "example": default, "hint": ""}


def rate_view(r, quoted, quoted_label, stats, note="", base=0):
    """Common result layout for modes that end in a 'real yearly rate'.
    base = what the thing costs without any financing (used for 'total you pay')."""
    real = r["real_rate"]
    top = max(real, quoted, 1)
    return {
        "headline_label": "Real yearly rate", "headline": pct(real),
        "headline_hint": "What this really costs you per year, after all charges.",
        "verdict": verdict(real),
        "bars": [
            {"label": quoted_label, "text": pct(quoted), "width": quoted / top * 100, "hot": False},
            {"label": "Rate you really pay", "text": pct(real), "width": real / top * 100, "hot": True},
        ],
        "stats": stats, "note": note,
        # plain numbers, used by the Compare page
        "real_rate": real, "extra_paid": r["extra_paid"], "total_paid": base + r["extra_paid"],
    }


# ---------- the runners: one per mode ----------
def run_normal(v):
    P, months = v["principal"], v["months"]
    fee_total = v["fee"] * (1.18 if v["gst"] else 1) + v["other"]
    if fee_total >= P:
        raise ValueError("The fee and other charges must be less than the loan amount.")
    r = normal_loan(P, v["rate"], months, fee_total)
    emis = r["emi"] * months                 # all EMIs added together
    total_back = emis + fee_total            # EMIs + fee and charges
    reaches = P - fee_total
    real = r["real_rate"]

    story = []
    if fee_total > 0:
        story.append(f"You borrow {inr(P)}, but after charges of {inr(fee_total)}, "
                     f"effectively only {inr(reaches)} reaches you.")
    else:
        story.append(f"You borrow {inr(P)} and all of it reaches you.")
    story.append(f"You repay {inr(r['emi'])} every month for {months_text(months)}. "
                 f"Together that is {inr(emis)}.")
    if fee_total > 0:
        story.append(f"Adding the {inr(fee_total)} of charges, you hand over {inr(total_back)} in all. "
                     f"This loan costs you {inr(r['extra_paid'])}.")
        story.append(f"The bank says {pct(v['rate'])} a year. After the charges, "
                     f"you really pay {pct(real)} a year.")
    else:
        story.append(f"In all you hand over {inr(total_back)}. "
                     f"This loan costs you {inr(r['extra_paid'])} in interest.")
        story.append(f"There are no extra charges, so the real rate is the same "
                     f"as the bank's rate: {pct(real)} a year.")

    stats = [("You pay every month (EMI)", inr(r["emi"])),
             ("Interest charged by the bank", inr(r["total_interest"]))]
    if fee_total > 0:
        stats.append(("Fee and other charges (with GST)", inr(fee_total)))
    stats += [("Total you pay back", inr(total_back)),
              ("Extra cost of this loan", inr(r["extra_paid"]))]

    _, rows = schedule(P, v["rate"], months)
    view = rate_view(r, v["rate"], "Rate the bank says", stats, "", base=P)
    view["story"] = story
    view["schedule"] = schedule_view(rows)
    return view


def run_flat(v):
    P, months, rate = v["principal"], v["months"], v["flat_rate"]
    fee_total = v["fee"] * (1.18 if v["gst"] else 1) + v["other"]
    if fee_total >= P:
        raise ValueError("The fee and other charges must be less than the loan amount.")
    f = flat_loan(P, rate, months)
    interest, monthly = f["total_interest"], f["emi"]
    emis = monthly * months                       # all EMIs added together
    total_back = emis + fee_total
    real = real_rate(P - fee_total, [monthly] * months)
    normal_interest = emi(P, rate, months) * months - P   # same rate, but a normal loan
    per_year = P * rate / 100

    story = []
    if fee_total > 0:
        story.append(f"You borrow {inr(P)}, but after charges of {inr(fee_total)}, "
                     f"effectively only {inr(P - fee_total)} reaches you.")
    else:
        story.append(f"You borrow {inr(P)} and all of it reaches you.")
    story.append(f"'Flat' means the bank charges {pct(rate)} on the full {inr(P)} every year, "
                 f"even though you keep paying it back. That is {inr(per_year)} a year, "
                 f"so {inr(interest)} over {months_text(months)}.")
    if fee_total > 0:
        story.append(f"You pay {inr(monthly)} every month. With the {inr(fee_total)} of charges, "
                     f"you hand over {inr(total_back)} in all. This loan costs you "
                     f"{inr(interest + fee_total)}.")
    else:
        story.append(f"You pay {inr(monthly)} every month. In all you pay back {inr(total_back)}, "
                     f"which is {inr(interest)} more than you borrowed.")
    if rate > 0:
        story.append(f"A normal bank loan at the same {pct(rate)} would charge only "
                     f"{inr(normal_interest)} interest, which is {inr(interest - normal_interest)} less. "
                     f"So '{pct(rate)} flat' really costs like a normal loan at {pct(real)} a year.")
        story.append(f"Time matters: every extra year adds {inr(per_year)} of interest, "
                     f"so a shorter loan costs you less.")

    stats = [("You pay every month (EMI)", inr(monthly)),
             ("Interest the bank charges (flat)", inr(interest)),
             (f"Interest on a normal loan at {pct(rate)}", inr(normal_interest))]
    if fee_total > 0:
        stats.append(("Fee and other charges (with GST)", inr(fee_total)))
    stats += [("Total you pay back", inr(total_back)),
              ("Extra cost of this loan", inr(interest + fee_total))]

    r = {"real_rate": real, "extra_paid": interest + fee_total}
    view = rate_view(r, rate, "Flat rate the bank says", stats, "", base=P)
    view["story"] = story
    view["schedule"] = schedule_view(
        flat_rows(P, rate, months),
        note=(f"Look at the interest column: it is {inr(P * rate / 1200)} every month, even in the "
              f"last month when you owe only {inr(P / months)}. A normal loan would charge far less "
              f"at the end. That is why a flat rate costs more."))
    return view


def run_nocost(v):
    price, cash, months = v["price"], v["cash_price"], v["months"]
    fee_total = v["fee"] * (1.18 if v["fee_gst"] else 1)
    if fee_total >= cash:
        raise ValueError("The fee must be less than the cash price.")
    r = no_cost_emi(price, cash, months, fee_total, v["gst"])
    hidden, gst, monthly = r["hidden_interest"], r["gst"], r["emi"]
    total, extra, real = r["total_paid"], r["extra_paid"], r["real_rate"]

    story = []
    if hidden > 0:
        story.append(f"The shop says 'No-Cost EMI'. But if you paid in full today it would cost "
                     f"{inr(cash)}, which is {inr(hidden)} less than the {inr(price)} on the EMI plan.")
        story.append(f"That {inr(hidden)} you give up is really the interest. "
                     f"It is just not called interest.")
    else:
        story.append(f"The EMI price and the cash price are the same ({inr(price)}), "
                     f"so you do not lose any discount.")
    extras = []
    if gst > 0:
        extras.append(f"{inr(gst)} GST on the hidden interest")
    if fee_total > 0:
        extras.append(f"a {inr(fee_total)} processing fee")
    if extras:
        story.append("On top of that, you pay " + " and ".join(extras) + ".")
    story.append(f"So you pay {inr(monthly)} every month for {months_text(months)}. "
                 f"In all you hand over {inr(total)}, against {inr(cash)} if you paid in full today.")
    if extra > 0.5:
        story.append(f"The shop says 0%. What you really pay is {pct(real)} a year, "
                     f"which is {inr(extra)} extra. {advice(verdict(real), extra)}")
    else:
        story.append("You pay nothing extra. This is a genuine zero-cost EMI.")

    stats = [("You pay every month (EMI)", inr(monthly))]
    if hidden > 0:
        stats.append(("Hidden interest (the discount you lose)", inr(hidden)))
    if gst > 0:
        stats.append(("GST on that interest", inr(gst)))
    if fee_total > 0:
        stats.append(("Processing fee" + (" (with GST)" if v["fee_gst"] else ""), inr(fee_total)))
    stats += [("Total you pay", inr(total)),
              ("Price if you pay in full today", inr(cash)),
              ("Extra cost of choosing EMI", inr(extra))]

    start = ("Start", "", "", inr(cash - fee_total))
    view = rate_view(r, 0, "What the shop says", stats, "", base=cash)
    view["story"] = story
    view["schedule"] = schedule_view(
        true_rows(cash - fee_total, [monthly] * months, real),
        start=start,
        note=(f"The shop shows no interest, but it is hidden inside your EMIs. You effectively "
              f"borrow {inr(cash - fee_total)} (the cash price{' minus the fee you pay up front' if fee_total > 0 else ''}). "
              f"This table splits each EMI at the real rate of {pct(real)}, so you can see the hidden interest."))
    return view


def run_zero(v):
    price, months = v["price"], v["months"]
    down, lost = v["down_payment"], v["discount_lost"]
    fee_total = v["fee"] * (1.18 if v["gst"] else 1)
    cash = price - lost                  # what a cash buyer would pay
    financed = price - down              # the part paid through monthly EMIs
    received = cash - down - fee_total   # what you really get on day one, after paying upfront
    if financed <= 0 or received <= 0:
        raise ValueError("The down payment and fee must be less than the price.")
    monthly = financed / months
    real = real_rate(received, [monthly] * months)
    total = price + fee_total
    extra = lost + fee_total

    story = []
    if lost > 0:
        story.append(f"The shop says 0% interest, but a cash buyer would pay {inr(cash)}, "
                     f"which is {inr(lost)} less than the {inr(price)} on the EMI plan. "
                     f"That {inr(lost)} is hidden interest.")
    else:
        story.append(f"The shop says 0% interest, and the EMI price is the same as the cash "
                     f"price ({inr(price)}), so no discount is lost.")
    if fee_total > 0:
        if v["gst"] and v["fee"] > 0:
            story.append(f"There is a processing fee of {inr(fee_total)} "
                         f"({inr(v['fee'])} + 18% GST).")
        else:
            story.append(f"There is a processing fee of {inr(fee_total)}.")
    else:
        story.append("There is no processing fee.")
    if down > 0:
        story.append(f"You pay {inr(down)} on day one, then {inr(monthly)} every month "
                     f"for {months_text(months)}.")
    else:
        story.append(f"You pay {inr(monthly)} every month for {months_text(months)}.")
    story.append(f"In all you hand over {inr(total)}, against {inr(cash)} if you paid in full today.")
    if extra > 0.5:
        story.append(f"That extra {inr(extra)} works out to {pct(real)} a year. "
                     f"{advice(verdict(real), extra)}")
    else:
        story.append("You pay nothing extra. This is a genuine 0% EMI.")

    stats = [("You pay every month (EMI)", inr(monthly))]
    if down > 0:
        stats.append(("Down payment today", inr(down)))
    if fee_total > 0:
        stats.append(("Processing fee" + (" (with GST)" if v["gst"] else ""), inr(fee_total)))
    if lost > 0:
        stats.append(("Discount you lose by choosing EMI", inr(lost)))
    stats += [("Total you pay", inr(total)),
              ("Price if you pay in full today", inr(cash)),
              ("Extra cost of choosing EMI", inr(extra))]

    r = {"real_rate": real, "extra_paid": extra}
    start = ("Start", "", "", inr(received))
    view = rate_view(r, 0, "What the shop says", stats, "", base=cash)
    view["story"] = story
    view["schedule"] = schedule_view(
        true_rows(received, [monthly] * months, real),
        start=start,
        note=(f"You effectively borrow {inr(received)} (the cash price, minus anything you pay on "
              f"day one). The shop shows 0%, but this table splits each EMI at the real rate of "
              f"{pct(real)}. The small interest here is the cost of the fee and any lost discount."))
    return view


def run_card(v):
    P, months, rate = v["price"], v["months"], v["rate"]
    fee_total = v["fee"] * (1.18 if v["gst"] else 1)
    if fee_total >= P:
        raise ValueError("The fee must be less than the purchase amount.")
    r = card_emi(P, rate, months, v["fee"], v["gst"])
    e, rows = schedule(P, rate, months)
    gst_total = r["gst_total"]
    total_back = e * months + gst_total + fee_total
    extra, real = r["extra_paid"], r["real_rate"]
    first_pay = e + rows[0][0] * 0.18
    last_pay = e + rows[-1][0] * 0.18

    story = []
    if fee_total > 0:
        fee_text = f" ({inr(v['fee'])} + 18% GST)" if v["gst"] else ""
        story.append(f"You turn a {inr(P)} purchase into EMI. The bank charges a {inr(fee_total)} "
                     f"fee{fee_text} up front, so you are effectively financing {inr(P - fee_total)}.")
    else:
        story.append(f"You turn a {inr(P)} purchase into EMI. There is no processing fee.")
    story.append(f"The bank's EMI is {inr(e)} a month for {months_text(months)}, "
                 f"at {pct(rate)} a year on what you still owe.")
    if gst_total > 0.5:
        story.append(f"On a credit card, 18% GST is also charged on the interest. That adds "
                     f"{inr(gst_total)} in all, so your monthly payment is a little more than the EMI: "
                     f"about {inr(first_pay)} in the first month, falling to {inr(last_pay)} in the last.")
    story.append(f"In all you hand over {inr(total_back)}. That is {inr(extra)} more than the "
                 f"{inr(P)} purchase.")
    story.append(f"The bank says {pct(rate)} a year. After GST and the fee, you really pay "
                 f"{pct(real)} a year.")

    stats = [("Bank's EMI (before GST)", inr(e)),
             ("Interest over the loan", inr(r["total_interest"])),
             ("GST on interest", inr(gst_total))]
    if fee_total > 0:
        stats.append(("Processing fee" + (" (with GST)" if v["gst"] else ""), inr(fee_total)))
    stats += [("Total you pay back", inr(total_back)),
              ("Extra cost of this EMI", inr(extra))]

    view = rate_view(r, rate, "Rate the bank says", stats,
                     "GST on interest applies to credit card EMIs. It does not apply to ordinary loans.",
                     base=P)
    view["story"] = story
    view["schedule"] = schedule_view(rows, "On a credit card, 18% GST is added on the interest part.")
    return view


def run_personal(v):
    P, months, rate = v["principal"], v["months"], v["rate"]
    base_fee = P * v["fee_percent"] / 100
    gst_on_fee = base_fee * 0.18 if v["gst"] else 0
    fee_total = base_fee + gst_on_fee + v["other"]
    if fee_total >= P:
        raise ValueError(f"The fees and charges come to {inr(fee_total)}, which is not less than the "
        f"loan of {inr(P)}. Check the fee box: it is a percentage of the loan, so "
        f"enter 2 for 2%. For a fixed fee in rupees, use 'Other charges' instead.")
    r = normal_loan(P, rate, months, fee_total)
    e, rows = schedule(P, rate, months)
    interest = r["total_interest"]
    total_back = e * months + fee_total
    real = r["real_rate"]

    story = []
    if fee_total > 0:
        parts = []
        if base_fee > 0:
            text = f"{pct(v['fee_percent'])} fee = {inr(base_fee)}"
            if v["gst"]:
                text += f" + {inr(gst_on_fee)} GST"
            parts.append(text)
        if v["other"] > 0:
            parts.append(f"{inr(v['other'])} other charges")
        story.append(f"You ask for {inr(P)}. The lender keeps {inr(fee_total)} as fees and charges "
                     f"({'; '.join(parts)}), so only {inr(P - fee_total)} reaches your account.")
    else:
        story.append(f"You borrow {inr(P)} and all of it reaches your account.")
    story.append(f"But your EMIs are worked out on the full {inr(P)}: {inr(e)} every month for "
                 f"{months_text(months)}. Together that is {inr(e * months)}.")
    if fee_total > 0:
        story.append(f"In all you hand over {inr(total_back)}: {inr(interest)} interest plus "
                     f"{inr(fee_total)} of fees and charges. So this loan costs you {inr(r['extra_paid'])}.")
        story.append(f"The lender says {pct(rate)} a year. After the fees, you really pay "
                     f"{pct(real)} a year.")
    else:
        story.append(f"In all you hand over {inr(total_back)}. This loan costs you "
                     f"{inr(interest)} in interest.")
        story.append(f"There are no fees, so the real rate is the same as the lender's rate: "
                     f"{pct(real)} a year.")

    stats = [("Money that reaches your account", inr(P - fee_total)),
             ("You pay every month (EMI)", inr(e)),
             ("Interest charged by the lender", inr(interest))]
    if fee_total > 0:
        stats.append(("Fees and charges" + (" (with GST)" if v["gst"] else ""), inr(fee_total)))
    stats += [("Total you pay back", inr(total_back)),
              ("Extra cost of this loan", inr(r["extra_paid"]))]

    view = rate_view(r, rate, "Rate the lender says", stats,
                     "On personal loans, GST is charged only on the fees, not on the interest.",
                     base=P)
    view["story"] = story
    view["schedule"] = schedule_view(rows)
    return view


def dues_plan(balance, monthly_rate, payment, gst):
    """Pay a fixed amount each month on card dues. Returns rows or None if the dues would never finish."""
    g = 0.18 if gst else 0.0
    bal, rows, interest_total, gst_total = balance, [], 0.0, 0.0
    if payment <= balance * monthly_rate / 100 * (1 + g):
        return None
    while bal > 0.01 and len(rows) < 1200:
        interest = bal * monthly_rate / 100
        tax = interest * g
        pay = min(payment, bal + interest + tax)
        repaid = pay - interest - tax
        bal -= repaid
        interest_total += interest
        gst_total += tax
        rows.append((interest + tax, repaid, max(bal, 0.0)))
    return {"rows": rows, "interest": interest_total, "gst": gst_total}


def run_dues(v):
    B, rate, pay, gst = v["balance"], v["monthly_rate"], v["payment"], v["gst"]
    plan = dues_plan(B, rate, pay, gst)
    if plan is None:
        raise ValueError("This payment is smaller than one month's interest, so the debt "
                         "would never finish. Try a larger monthly payment.")
    rows, interest, tax = plan["rows"], plan["interest"], plan["gst"]
    months = len(rows)
    cost = interest + tax
    simple = rate * 12
    compounded = ((1 + rate / 100) ** 12 - 1) * 100
    first_interest = B * rate / 100
    first_tax = first_interest * 0.18 if gst else 0

    story = [f"You owe {inr(B)} on your card. The bank charges {rate:g}% every month on what you have "
             f"not paid. In month 1 that is {inr(first_interest)}"
             + (f", plus {inr(first_tax)} GST." if gst else ".")]
    story.append(f"You pay {inr(pay)} a month. After the interest"
                 + (" and GST" if gst else "")
                 + f", only {inr(min(B, pay - first_interest - first_tax))} of it reduces what you owe in month 1.")
    story.append(f"It takes {months_text(months)} to clear the dues. In all you pay {inr(B + cost)}: "
                 f"your {inr(B)} dues, {inr(interest)} interest"
                 + (f" and {inr(tax)} GST." if gst else "."))
    level = verdict(compounded)
    story.append(f"{rate:g}% a month is {pct(simple)} a year, or {pct(compounded)} with compounding. "
                 f"{'GST makes it even higher. ' if gst else ''}"
                 f"{'That is low.' if level == 'Fair' else 'That is ' + level.lower() + '.'}")
    better = dues_plan(B, rate, pay * 2, gst)
    if better:
        saved = cost - (better["interest"] + better["gst"])
        story.append(f"If you paid {inr(pay * 2)} a month instead, you would finish in "
                     f"{months_text(len(better['rows']))} and pay {inr(saved)} less interest"
                     + (" and GST." if gst else "."))

    top = max(compounded, simple, 1)
    stats = [("You pay every month", inr(pay)),
             ("Months to clear the dues", months_text(months)),
             ("Interest charged", inr(interest))]
    if gst:
        stats.append(("GST on the interest", inr(tax)))
    stats.append(("Total you pay back", inr(B + cost)))
    return {
        "headline_label": "Interest" + (" and GST" if gst else "") + " you will pay",
        "headline": inr(cost),
        "headline_hint": "What carrying these dues costs you.",
        "verdict": verdict(compounded),
        "bars": [
            {"label": f"{rate:g}% x 12 months", "text": pct(simple),
             "width": simple / top * 100, "hot": False},
            {"label": "Real yearly (compounded)", "text": pct(compounded),
             "width": compounded / top * 100, "hot": True},
        ],
        "story": story, "stats": stats,
        "note": "On credit cards, GST is charged on the interest. The yearly rates shown here are before GST.",
        "schedule": table_view(
            ["Month", "Interest" + (" + GST" if gst else ""), "Dues repaid", "Still owed"],
            [(str(k + 1), inr(i), inr(p), inr(b)) for k, (i, p, b) in enumerate(rows)],
            "Each month the interest" + (" and GST are" if gst else " is") +
            " taken out of your payment first. Only what is left reduces your dues, "
            "so a small payment barely moves the balance."),
    }


def run_prepay(v):
    P, rate, months, extra = v["principal"], v["rate"], v["months"], v["extra"]
    paid, charge_pct = v["paid"], v["charge"]
    if extra <= 0:
        raise ValueError("Enter an extra amount that is more than zero.")
    if paid >= months:
        raise ValueError("The EMIs already paid must be fewer than the total loan months.")
    e, plan = schedule(P, rate, months)
    owed = P if paid == 0 else plan[paid - 1][2]       # what you still owe today
    left = months - paid
    r = rate / 1200

    def run(extra_amount):
        bal, rows, interest_total, extra_total = owed, [], 0.0, 0.0
        while bal > 0.01 and len(rows) < 2000:
            i = bal * r
            pay = min(e + extra_amount, bal + i)
            bal += i - pay
            interest_total += i
            extra_total += max(pay - e, 0)
            rows.append((i, pay - i, max(bal, 0.0)))
        return rows, interest_total, extra_total

    normal, int_normal, _ = run(0)
    faster, int_faster, extra_total = run(extra)
    charge = extra_total * charge_pct / 100 * 1.18
    saved = int_normal - int_faster
    net = saved - charge
    saved_months = len(normal) - len(faster)

    story = [f"Your loan is {inr(P)} at {pct(rate)} for {months_text(months)}. The EMI is {inr(e)}."]
    if paid > 0:
        story.append(f"You have already paid {paid} EMIs, so you still owe {inr(owed)} with "
                     f"{months_text(left)} to go.")
    story.append(f"If you keep paying only the EMI, you pay {inr(int_normal)} more interest in total.")
    story.append(f"If you pay {inr(extra)} extra every month, the loan finishes in "
                 f"{months_text(len(faster))} instead of {months_text(len(normal))}"
                 + (f", which is {months_text(saved_months)} earlier" if saved_months > 0 else "")
                 + f". The interest falls to {inr(int_faster)}.")
    if charge > 0:
        story.append(f"You save {inr(saved)} of interest, but the lender charges {inr(charge)} for "
                     f"prepayment (with 18% GST). So your real saving is {inr(net)}."
                     + ("" if net > 0 else " That is not worth it."))
    else:
        story.append(f"Your extra payments (about {inr(extra_total)} in all) repay the loan faster, "
                     f"so you save {inr(saved)} of interest.")

    stats = [("Your EMI", inr(e))]
    if paid > 0:
        stats.append(("Still owed today", inr(owed)))
    stats += [("Interest if you pay only the EMI", inr(int_normal)),
              ("Interest with the extra payment", inr(int_faster)),
              ("Time saved", months_text(saved_months) if saved_months > 0 else "None"),
              ("Extra payments in total", inr(extra_total))]
    if charge > 0:
        stats.append(("Prepayment charge (with GST)", inr(charge)))
    stats.append(("Your saving", inr(net)))

    text = []
    for k, (i, p, b) in enumerate(faster):
        normal_owed = normal[k][2] if k < len(normal) else 0.0
        text.append((str(k + 1), inr(i), inr(p), inr(b), inr(normal_owed)))
    return {
        "headline_label": "Interest you save", "headline": inr(net),
        "headline_hint": "After paying " + inr(extra) + " extra every month"
                         + (" and the prepayment charge." if charge > 0 else "."),
        "verdict": None, "bars": None, "story": story, "stats": stats,
        "note": "Ask the lender if there is any charge for part-prepayment before you do it.",
        "schedule": table_view(
            ["Month", "Interest", "Loan repaid", "Owed with extra", "Owed normally"], text,
            "Months are counted from today. With the extra payment, more of each month goes to the "
            "loan, so the interest shrinks faster and you finish earlier."),
    }


# ---------- the list of modes shown on the site ----------
MODES = {
    "no-cost-emi": {
        "title": "No-Cost EMI", "short": "The shop says 'No-Cost EMI' or 'zero interest'.",
        "says": "Shop says: 'Pay ₹5,000 for 6 months. No extra cost.' Find out what it really costs.",
        "fields": [num("price", "Price on the EMI plan (₹)", "The total of all your EMIs. Example: ₹5,000 x 6 months = ₹30,000.", 30000),
                   num("cash_price", "Price if you pay in full today (₹)", "Ask the shop: 'What is the price if I pay by cash or card instead of EMI?' Include any discount you would lose by choosing EMI.", 28500),
                   num("months", "For how many months?", "", 6),
                   num("fee", "Processing fee (₹)", "Enter 0 if none.", 199, "0"),
                   check("fee_gst", "The offer says the fee is '+ GST' or 'plus taxes'", False),
                   check("gst", "GST (18%) is charged on the hidden interest (yes for credit card EMIs, usually no for loan-based EMI cards)")],
        "run": run_nocost,
        "ints": ["months"],
        "tips": ["What is the price if I pay in full today instead of EMI?",
                 "Is there a processing fee, and is GST added on top?",
                 "Is GST charged on the interest?",
                 "Is there a charge if I close the EMI early?",
                 "Will I lose any card or bank offer by choosing EMI?"],
    },
    "zero-percent": {
        "title": "0% EMI with a fee", "short": "0% interest, but a processing fee applies.",
        "says": "Shop says: '0% interest, only a small processing fee.' Check if it is really a fair deal.",
        "fields": [num("price", "Price on the EMI plan (₹)", "Usually the same as the normal price.", 60000),
                   num("down_payment", "Down payment (₹)", "Money you pay on day one, besides the fee. Enter 0 if none.", 0, "0"),
                   num("months", "Number of monthly EMIs", "After any down payment.", 9),
                   num("fee", "Processing fee (₹)", "Before GST. Enter 0 if none.", 1000, "0"),
                   check("gst", "GST (18%) is added on the fee (usually yes)"),
                   num("discount_lost", "Cash discount you lose by choosing EMI (₹)", "Ask: 'Do I get any discount if I pay in full?' Enter 0 if none.", 0, "0")],
        "run": run_zero, "ints": ["months"],
        "tips": ["Is the EMI price the same as the cash price?",
                 "What exactly is the fee, and is GST added on top?",
                 "Do I pay any EMI or amount on day one?",
                 "Is there a charge if I close the EMI early?",
                 "Are there other charges, like documentation or convenience fees?"],
    },
    "flat-rate": {
        "title": "Flat-rate loan", "short": "The offer says 'only 8% flat'.",
        "says": "Common for cars, bikes and appliances. 'Only 8% flat' sounds cheap, but the "
                "interest is charged on the full amount for the whole time.",
        "fields": [num("principal", "How much are you borrowing? (₹)", "For a car or bike, this is the price minus your down payment.", 1000000),
                   num("flat_rate", "Flat rate the seller says (% per year)", "The rate written on the offer, like 8.", 8),
                   num("months", "For how many months?", "1 year = 12 months, 3 years = 36.", 36),
                   num("fee", "Processing fee (₹)", "A one-time charge for giving you the loan. Enter 0 if none.", 0, "0"),
                   check("gst", "The lender adds 18% GST on this fee (most do)"),
                   num("other", "Other charges taken upfront (₹)", "Insurance, documentation, stamp duty. Enter 0 if none.", 0, "0")],
        "run": run_flat, "ints": ["months"],
        "tips": ["Is this a flat rate or a reducing-balance rate?",
                 "What is the total amount I will pay back?",
                 "What is the processing fee, and is GST added on it?",
                 "Is there insurance or any other charge cut from the loan?",
                 "Can I pay the loan off early, and will I get back some of the interest?"],
    },
    "credit-card-emi": {
        "title": "Credit card EMI", "short": "Converting a card purchase into EMI.",
        "says": "Bank says: 'Convert to EMI at 15% a year.' But credit cards add GST on the interest, "
                "and there is a fee on top.",
        "fields": [num("price", "Purchase amount you are converting (₹)", "", 50000),
                   num("rate", "Interest rate the bank says (% per year)", "If the offer shows a monthly rate like 1.25%, multiply by 12 (that is 15%).", 15),
                   num("months", "For how many months?", "", 12),
                   num("fee", "Processing fee (₹)", "Many banks charge about ₹199 to ₹499. Enter 0 if the bank says nil.", 499, "0"),
                   check("gst", "18% GST is added on this fee (most banks do)")],
        "run": run_card, "ints": ["months"],
        "tips": ["What is the interest rate, per year or per month?",
                 "What is the processing fee, and is GST added on it?",
                 "Is there a charge if I close the EMI early (pre-closure)?",
                 "Does the bank show the total amount I will pay?"],
    },
    "personal-loan": {
        "title": "Personal loan with fees", "short": "Instant loan with a processing fee.",
        "says": "Lender says: 'Loan at 14%, only 2% processing fee.' The fee is cut before the money "
                "reaches you, but you repay the full amount.",
        "fields": [num("principal", "How much are you borrowing? (₹)", "The loan amount.", 200000),
                   num("rate", "Interest rate the lender says (% per year)", "Written on the offer, like 14.", 14),
                   num("months", "For how many months?", "1 year = 12 months, 2 years = 24.", 24),
                   num("fee_percent", "Processing fee (% of the loan)", "Usually 1% to 3%. Enter 0 if none.", 2, "0"),
                   check("gst", "18% GST is added on this fee (most lenders add it)"),
                   num("other", "Other charges taken upfront (₹)", "Insurance, documentation, or a fixed fee in rupees. Enter 0 if none.", 0, "0")],
        "run": run_personal, "ints": ["months"],
        "tips": ["How much exactly will reach my bank account?",
                 "Is the fee a percentage or a fixed amount, and is GST added on top?",
                 "Is insurance or any other charge cut from the loan?",
                 "What is the charge if I repay early (foreclosure)?"],
    },
    "normal-loan": {
        "title": "Normal bank loan", "short": "A standard loan from a bank at a yearly rate.",
        "says": "A normal loan from a bank. Use it to see what a loan really costs after fees, "
                "and to compare other offers against it.",
        "fields": [num("principal", "How much are you borrowing? (₹)", "The loan amount.", 100000),
                   num("rate", "Interest rate the bank says (% per year)", "Written on the offer, like 12 or 10.5.", 12),
                   num("months", "For how many months?", "1 year = 12 months, 2 years = 24.", 12),
                   num("fee", "Processing fee (₹)", "A one-time charge for giving you the loan. Enter 0 if none.", 1000, "0"),
                   check("gst", "The bank adds 18% GST on this fee (most banks do)"),
                   num("other", "Other charges taken upfront (₹)", "Loan insurance, documentation, stamp duty. Enter 0 if none.", 0, "0")],
        "run": run_normal, "ints": ["months"],
        "tips": ["What is the processing fee, and is GST added on it?",
                 "Is there any insurance or other charge cut from the loan?",
                 "Is the interest rate fixed, or can it change later?",
                 "Can I pay the loan off early without a penalty?"],
    },
    "card-dues": {
        "title": "Unpaid credit card dues", "short": "Paying only the 'minimum due'.",
        "says": "Not paying your full card bill? The bank charges interest every month on what is "
                "left. See how long it takes and what it costs.",
        "fields": [num("balance", "How much do you owe on the card? (₹)", "The unpaid amount.", 20000),
                   num("monthly_rate", "Interest the card charges per month (%)", "Check your statement. Many cards charge around 3.5% a month. If it shows a yearly rate like 42%, divide by 12.", 3.5),
                   num("payment", "How much can you pay every month? (₹)", "Try the 'minimum amount due' from your statement to see the trap.", 1000),
                   check("gst", "18% GST is added on the interest (yes on credit cards)")],
        "run": run_dues, "ints": [],
        "tips": ["What is the interest rate per month on unpaid dues?",
                 "Is GST added on the interest?",
                 "Can I convert the dues into an EMI at a lower rate?",
                 "Do I lose the interest-free period on new purchases if I do not pay in full?"],
    },
    "prepay": {
        "title": "Close my loan early", "short": "See what paying extra each month saves.",
        "says": "Pay a little extra every month and see how much time and interest you save. "
                "Check if any prepayment charge cancels the saving.",
        "fields": [num("principal", "Original loan amount (₹)", "The amount you first borrowed.", 500000),
                   num("rate", "Interest rate (% per year)", "", 10),
                   num("months", "Total loan period (months)", "1 year = 12 months, 5 years = 60.", 60),
                   num("paid", "How many EMIs have you already paid?", "Enter 0 if you are just starting.", 0, "0"),
                   num("extra", "Extra you can pay every month (₹)", "On top of your normal EMI.", 2000),
                   num("charge", "Prepayment charge (% of the extra amount)", "Some lenders charge nothing, others a few percent. Ask your lender. Enter 0 if none.", 0, "0")],
        "run": run_prepay, "ints": ["months", "paid"],
        "tips": ["Is there a prepayment or foreclosure charge, and is GST added on it?",
                 "Will extra payment reduce the loan period or the EMI?",
                 "Is there a minimum amount for part-prepayment?",
                 "Is the interest rate fixed or floating?"],
    },
}


# ---------- extra pieces for the Compare page ----------
def run_cash(v):
    return {"real_rate": 0.0, "extra_paid": 0.0, "total_paid": v["price"], "verdict": None,
            "headline_label": "", "headline": "", "bars": None, "stats": [], "note": ""}


CASH_MODE = {
        "title": "Pay cash", "short": "Pay the full price today by cash, UPI or card. No EMI, no interest.", "says": "Pay the full price today (cash, UPI or debit card).",
    "fields": [num("price", "Cash price, ₹", "The price after any cash discount.", 28500)],
    "run": run_cash, "ints": [], "tips": [],
}

COMPARE_KEYS = ["no-cost-emi", "zero-percent", "flat-rate", "credit-card-emi",
                "personal-loan", "normal-loan"]
COMPARE_MODES = {k: MODES[k] for k in COMPARE_KEYS}
COMPARE_MODES["cash"] = CASH_MODE