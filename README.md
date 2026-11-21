# EMI Truth Meter

**Find the real cost hiding behind No-Cost EMI, flat-rate and loan offers.**

A small web app for the public. You type the numbers from an offer, and it shows the **real yearly interest rate**, the **extra rupees you pay**, and the whole story in plain words, with a month-by-month table.

Mini project, B.Tech, KCC Institute of Technology and Management (CC 492), 2026.

> Live demo: https://emi-truth-meter.vercel.app/

---

## Why this project

Shops say *"No-Cost EMI"*, *"0% interest"* or *"just 8% flat"*, and it sounds like you pay nothing extra. But the cost is often hidden in a lost cash discount, a processing fee, or tax on interest. These costs are real, but they are spread across the bill, so nobody adds them up. This app adds them up.

Example: a ₹30,000 phone on a "6 month No-Cost EMI" really costs about **23.5% a year**, not 0%.

## What it can check

| Offer | What it shows |
|---|---|
| **No-Cost EMI** | The hidden interest (the discount you lose), GST, the fee, the real rate |
| **0% EMI with a fee** | Whether it is really a fair deal, with down payment and lost discount |
| **Flat-rate loan** | Why "8% flat" is really about 14.5%, compared with a normal loan |
| **Credit card EMI** | GST on interest, the fee, the real rate |
| **Personal loan with fees** | The fee cut before the money reaches you, the real rate |
| **Normal bank loan** | The baseline, with fee, GST and other charges |
| **Unpaid credit card dues** | How long dues take to clear and what the "minimum due" really costs |
| **Close my loan early** | Interest and time saved by paying extra, with EMIs already paid and any prepayment charge |
| **Compare two offers** | Two offers side by side (or an EMI against paying cash), each with its own months and fees |

Every result page has:
- the **real yearly rate** and a verdict (Fair, Costly or Very costly),
- an **"In plain words"** explanation,
- a **month-by-month table** (interest, loan repaid, still owed),
- an **"Ask the shop"** checklist.

## How it works

1. **EMI formula** for a normal loan:
   `EMI = P x r x (1+r)^n / ((1+r)^n - 1)`
   where P is the amount, r the monthly rate and n the number of months.
2. **Real rate:** there is no direct formula, so the program plays a "higher or lower" guessing game. It guesses a monthly rate, checks whether the EMIs add up to the money you actually received, then raises or lowers the guess. After about 100 rounds the answer is accurate. Multiply by 12 for the yearly rate.
3. **Verdict (our own guide):** up to 10% a year is Fair, 10% to 18% is Costly, above 18% is Very costly.

No database is used. Nothing the user types is stored.

## Tech stack

- Python 3, Flask
- HTML, CSS and a little JavaScript
- pytest for testing

## Run it on your computer

You need Python 3.11 or newer.

```powershell
git clone https://github.com/[kovidsharma27]/emi-truth-meter.git
cd emi-truth-meter

py -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

`python app.py` starts Flask in debug mode, which is only for your own computer. To run without debug mode:

```powershell
flask --app app run --port 5000
```

## Run the tests

```powershell
python -m pytest -q
```

The tests check every example in the project guide (for example No-Cost EMI 23.5%, flat 12% for one year 21.5%, personal loan 16.4%), plus bad inputs and page behaviour.

## Project structure

```
emi-truth-meter/
├── app.py                  # Flask routes: home, one page per offer, compare
├── modes.py                # Each offer: its boxes, how to run it, how to explain it
├── engine/
│   └── calculators.py      # The maths: EMI, real rate, loan formulas
├── templates/
│   ├── base.html           # Common header and footer
│   ├── index.html          # Home page with the offer cards
│   ├── calculator.html     # One template used by every offer page
│   └── compare.html        # Compare two offers
├── public/
│   ├── style.css           # Cream, black and dark pink design
│   └── script.js           # Switches the boxes on the Compare page
├── tests/
│   ├── test_engine.py      # Tests for the maths
│   └── test_app.py         # Tests for the pages
└── requirements.txt
```

## Assumptions and limits

The results are estimates. They rest on these assumptions:

- The interest rate stays **fixed** for the whole loan.
- EMIs are paid at the **end of each month**.
- Fees and other charges are taken **upfront**.
- GST of 18% is applied on fees. On credit card EMIs and card dues it is also applied on the interest. On ordinary loans, interest has no GST.
- **No-Cost EMI:** the hidden interest is estimated as the gap between the EMI price and the cash price the user enters.
- **Flat-rate loans:** refund of interest on early closing is not modelled, because lenders differ.
- **Advance EMI** (first EMI paid at purchase) has no separate box. Enter it as a down payment and reduce the months by one.
- **Card dues:** new purchases and late fees are ignored.
- **Prepayment:** extra money is assumed to reduce the loan balance every month. The prepayment charge is entered by the user.
- Banks round the EMI to whole rupees and adjust the last EMI, so figures can differ by a few rupees from a bank statement.

## Future updates

- Hindi version of the pages
- Save or share the result as an image or PDF
- Floating-rate loans, where the rate changes over time
- More offer types (for example Buy Now Pay Later and gold loans)
- Preset values for common banks and shops

## Disclaimer

Educational project. The app gives estimates from the numbers you enter. It is not financial advice and does not replace a bank or a financial adviser. Offer terms, fees and tax rules differ by lender and can change.

## Team

| Name | Role |
|---|---|
| [Kovid Sharma] | [Developer] |
| [Name] | [Researcher] |
| [Name] | [Tester] |
| [Name] | [Report writer] |
| [Name] | [Presenter] |

Project guide: [Faculty name]  
Department of CSE, KCC Institute of Technology and Management, Greater Noida.