from flask import Flask, render_template, request, abort
from modes import MODES, COMPARE_MODES
from modes import inr, pct, months_text

# Vercel serves static files from the "public" folder, so Flask uses the same folder locally.
app = Flask(__name__, static_folder="public", static_url_path="")

MAX_MONEY = 1_000_000_000      # 100 crore, just a sanity limit
MAX_MONTHS = 600               # 50 years


def read_form(mode, data, prefix=""):
    """Read form boxes into numbers. Raises ValueError with a friendly message.
    prefix is used on the Compare page ('a_' or 'b_')."""
    values = {}
    for f in mode["fields"]:
        key = prefix + f["name"]
        if f["kind"] == "check":
            values[f["name"]] = key in data
            continue
        raw = data.get(key, "").strip()
        try:
            x = float(raw)
        except ValueError:
            raise ValueError(f"Please enter a number for: {f['label']}")
        if x < 0:
            raise ValueError(f"'{f['label']}' cannot be negative.")
        if x > MAX_MONEY:
            raise ValueError(f"'{f['label']}' is too large.")
        values[f["name"]] = int(x) if f["name"] in mode["ints"] else x
    if "months" in values and not (1 <= values["months"] <= MAX_MONTHS):
        raise ValueError(f"Number of months must be between 1 and {MAX_MONTHS}.")
    for key in ("principal", "price", "balance"):
        if key in values and values[key] <= 0:
            raise ValueError("The amount must be more than zero.")
    if "cash_price" in values:
        if values["cash_price"] <= 0:
            raise ValueError("Cash price must be more than zero.")
        if values["cash_price"] > values["price"]:
            raise ValueError("Cash price cannot be more than the EMI price.")
    if "discount_lost" in values and values["discount_lost"] >= values["price"]:
        raise ValueError("Discount lost must be less than the product price.")
    return values


@app.route("/")
def home():
    return render_template("index.html", modes=MODES)


@app.route("/calc/<key>", methods=["GET", "POST"])
def calc(key):
    mode = MODES.get(key)
    if mode is None:
        abort(404)
    result, error = None, None
    if request.method == "POST":
        shown = {f["name"]: (f["name"] in request.form) if f["kind"] == "check"
                 else request.form.get(f["name"], "") for f in mode["fields"]}
        try:
            result = mode["run"](read_form(mode, request.form))
        except ValueError as e:
            error = str(e)
    elif request.args.get("example"):
        shown = {f["name"]: f["example"] for f in mode["fields"]}
    else:
        shown = {f["name"]: f["default"] for f in mode["fields"]}
    return render_template("calculator.html", key=key, mode=mode, values=shown,
                           result=result, error=error)


@app.route("/compare", methods=["GET", "POST"])
def compare():
    # blank form: every offer type has its own set of boxes for both sides
    values = {s: {k: {f["name"]: f["default"] for f in m["fields"]}
                  for k, m in COMPARE_MODES.items()} for s in "ab"}
    sel = {"a": "no-cost-emi", "b": "cash"}
    results, error = None, None

    if request.method == "GET" and request.args.get("example"):
        for s in "ab":
            values[s][sel[s]] = {f["name"]: f["example"] for f in COMPARE_MODES[sel[s]]["fields"]}

    if request.method == "POST":
        items = []
        try:
            for s, name in (("a", "Offer A"), ("b", "Offer B")):
                key = request.form.get(s + "_mode", "")
                if key not in COMPARE_MODES:
                    raise ValueError(f"{name}: please choose a type of offer.")
                sel[s] = key
                mode = COMPARE_MODES[key]
                values[s][key] = {f["name"]: (s + "_" + f["name"] in request.form)
                                  if f["kind"] == "check"
                                  else request.form.get(s + "_" + f["name"], "")
                                  for f in mode["fields"]}
                try:
                    parsed = read_form(mode, request.form, s + "_")
                    view = mode["run"](parsed)
                except ValueError as e:
                    raise ValueError(f"{name}: {e}")
                items.append({"name": name, "key": key, "title": mode["title"], "view": view,
                              "total": inr(view["total_paid"]), "extra": inr(view["extra_paid"]),
                              "rate": pct(view["real_rate"]),
                              "months_n": parsed.get("months"),
                              "months": months_text(parsed["months"]) if "months" in parsed else None,
                              "monthly": view["stats"][0] if view.get("stats") else None})
            a, b = items[0]["view"]["total_paid"], items[1]["view"]["total_paid"]
            diff = abs(a - b)
            if diff < 1:
                headline = "Both offers cost the same in total."
            else:
                win = items[0] if a < b else items[1]
                headline = f"{win['name']} costs {inr(diff)} less in total."
            items[0]["best"] = diff >= 1 and a < b
            items[1]["best"] = diff >= 1 and b < a

            # extra lines that help when the two offers are not alike
            rate_line = tenure_note = None
            if items[0]["key"] != "cash" and items[1]["key"] != "cash":
                ra, rb = items[0]["view"]["real_rate"], items[1]["view"]["real_rate"]
                if abs(ra - rb) < 0.05:
                    rate_line = "Both offers have the same real yearly rate."
                else:
                    low = items[0] if ra < rb else items[1]
                    rate_line = (f"{low['name']} has the lower real yearly rate "
                                 f"({pct(min(ra, rb))} against {pct(max(ra, rb))}).")
            ma, mb = items[0]["months_n"], items[1]["months_n"]
            if ma and mb and ma != mb:
                tenure_note = (f"The offers run for different lengths of time ({ma} months and "
                               f"{mb} months), so look at the total you pay and the real "
                               f"yearly rate together.")
            results = {"items": items, "headline": headline,
                       "rate_line": rate_line, "tenure_note": tenure_note}
        except ValueError as e:
            error = str(e)

    return render_template("compare.html", cmodes=COMPARE_MODES, values=values, sel=sel,
                           results=results, error=error)


@app.errorhandler(404)
def not_found(e):
    return render_template("index.html", modes=MODES, missing=True), 404


if __name__ == "__main__":
    app.run(debug=True)