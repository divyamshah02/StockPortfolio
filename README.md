Indian Stock Portfolio Manager

A simple web-based application built with Django to manage and analyze an Indian equity stock portfolio.

The application records every buy and sell trade, automatically calculates holdings and average prices, tracks realized and unrealized profit/loss, and provides portfolio-level and trading-script-level performance insights.

Features
Portfolio Management
Add BUY and SELL trades.
Store complete trade history for every stock.
Automatically calculate:
Total quantity held
Average buy price
Current market value
Invested amount
Realized profit/loss
Unrealized profit/loss
Overall portfolio profit/loss
View individual stock holdings along with their complete historical trades.
Maintain the complete transaction history without overwriting previous trades.
Stock Validation & Current Price

When adding a trade, the user can enter a stock symbol and use a small Check action to validate the stock.

The application can retrieve the stock information/current market price using Yahoo Finance (yfinance).

For every trade, the application stores the actual trade price entered by the user rather than relying on the current market price.

This allows historical trades to remain accurate even when the market price changes later.

Buy Example

Suppose the following trades are entered:

Date	Stock	Type	Quantity	Price
05 Aug 2026	RELIANCE	BUY	100	₹500
13 Aug 2026	RELIANCE	BUY	50	₹550

The portfolio will show:

Quantity: 150
Average price: ₹516.67
Invested amount: ₹77,500

The original trades remain available in the trade history.

Sell Example

If the user subsequently sells:

Date	Stock	Type	Quantity	Price
20 Aug 2026	RELIANCE	SELL	20	₹570

The application should:

Reduce the current holding from 150 to 130 shares.
Calculate the realized profit from the 20 shares sold.
Calculate the remaining holding and its average cost.
Update the overall portfolio statistics.
Keep the SELL trade permanently in the transaction history.

The application should use a clearly defined cost-basis method for calculating realized P/L. The initial implementation can use weighted-average cost.

Trading Scripts

The application supports different trading strategies/scripts.

For example:

Long Term
Swing Trading
Breakout
Momentum
Dividend
Intraday
Custom Strategy

Each trade can be associated with a Script.

This makes it possible to analyze which trading strategy is actually performing well.

For each script, the application can eventually show:

Total trades
Buy trades
Sell trades
Total realized profit/loss
Winning trades
Losing trades
Win rate
Average profit
Average loss
Best performing stock
Worst performing stock
Overall return

A new script should be creatable directly while adding a trade, so the user does not have to leave the trade form.

Dashboard

The main dashboard should provide a quick overview of the entire portfolio.

Possible dashboard sections include:

Portfolio Summary
Total invested amount
Current portfolio value
Total realized P/L
Total unrealized P/L
Total P/L
Number of stocks currently held
Number of profitable holdings
Number of loss-making holdings
Holdings

A stock-wise table containing:

Stock	Qty	Avg. Price	Current Price	Invested	Current Value	P/L	P/L %
Trade History

Display every transaction with:

Date
Stock
Buy/Sell
Quantity
Trade price
Total trade value
Script
Notes, if applicable
Created/updated timestamp
Performance Charts

The dashboard should support charts such as:

Portfolio value
Profit/loss over time
Stock-wise allocation
Stock-wise P/L
Realized vs unrealized P/L
Script-wise performance
Winning vs losing trades

Charts should be kept simple and useful rather than adding unnecessary complexity.

Database Models

The initial application should contain the following core models.

UserDetail

Stores application-specific information for the logged-in user.

The Django authentication system should be used for login/authentication, while UserDetail can contain additional user-specific information if required.

Possible fields:

user
created_at
updated_at
Script

Represents a trading strategy/script.

Suggested fields:

user
name
description
created_at
updated_at
is_active

A user should only be able to access their own scripts.

Trade

Stores every individual BUY or SELL transaction.

Suggested fields:

user
script
stock_symbol
trade_type
quantity
price
trade_date
notes
created_at
updated_at

Where:

trade_type = BUY or SELL
quantity = number of shares
price = actual execution/trade price
trade_date = date/time when the trade occurred

The trade model should represent the transaction itself and should never be modified automatically based on current market prices.

Portfolio Calculation

Portfolio values should be calculated from the stored trades.

For a stock:

Current Quantity =
Total BUY Quantity - Total SELL Quantity


For weighted-average cost:

Average Cost =
Total Cost of Remaining Holdings / Remaining Quantity


The system should distinguish between:

Realized P/L — profit/loss from shares that have already been sold.
Unrealized P/L — profit/loss on shares that are still held.
Total P/L — realized P/L + unrealized P/L.

Current market price should come from the market-price provider, while historical trade prices should always come from the stored trade record.

Stock Price Service

Stock-price retrieval should be isolated into a dedicated service instead of putting yfinance logic directly inside models or templates.

For example:

services/
    stock_price.py


The service can provide functionality such as:

get_stock_price(symbol)
validate_stock(symbol)


The stock symbol validation action can be used by the trade form to confirm that the entered stock exists and optionally display its current price.

For Indian stocks, the appropriate Yahoo Finance symbol format should be used, such as:

RELIANCE.NS
TCS.NS
INFY.NS
HDFCBANK.NS


The exact symbol should be stored consistently so that price lookups remain reliable.

Application Structure

A possible Django project structure:

stock_portfolio/
│
├── manage.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── portfolio/
│   ├── migrations/
│   ├── templates/
│   │   └── portfolio/
│   ├── static/
│   │   └── portfolio/
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── services/
│       ├── portfolio.py
│       └── stock_price.py
│
├── requirements.txt
├── .env.example
└── README.md

Main Pages
Login

User authentication.

Dashboard

Overall portfolio summary, holdings, P/L and charts.

Add Trade

Simple form:

Trade Type:     BUY / SELL
Stock Symbol:   [ RELIANCE ] [Check]
Quantity:       [ 100 ]
Trade Price:    [ 500 ]
Trade Date:     [ 05-08-2026 ]
Script:         [ Long Term ▼ ] [+ Add Script]
Notes:          [ Optional ]

                [ Save Trade ]


When Check is clicked, the application should validate the stock symbol and display useful information such as:

✓ Valid Stock

RELIANCE
Current Price: ₹...


The current market price should not replace the historical trade price entered by the user.

Holdings

A stock-wise view of the current portfolio.

Clicking a stock should open its detailed page.

Stock Detail

For example:

RELIANCE

Current Quantity: 130
Average Price: ₹516.67
Current Price: ₹570
Invested Value: ...
Current Value: ...
Unrealized P/L: ...

Trade History
------------------------------------------------
05 Aug 2026   BUY    100   ₹500
13 Aug 2026   BUY     50   ₹550
20 Aug 2026   SELL    20   ₹570

Scripts

Display all trading scripts and their performance.

Example:

Script              Invested       Realized P/L
------------------------------------------------
Long Term            ₹...             ₹...
Swing Trading        ₹...             ₹...
Momentum             ₹...             ₹...


Clicking a script should show the trades and performance associated with it.

Trade History

A complete searchable/filterable list of all trades.

Filters can include:

Stock
BUY/SELL
Script
Date range
Profit/loss
User
Data Integrity

The application should enforce important validation rules.

A user cannot sell more shares than they currently own.
Quantity must be greater than zero.
Trade price must be greater than zero.
Trade type must be either BUY or SELL.
A trade must belong to the authenticated user.
A script must belong to the same authenticated user.
Historical trade prices must never be overwritten by current market prices.
Deleting or editing a historical trade should trigger portfolio recalculation.
Portfolio calculations should be based on transaction history rather than manually stored portfolio totals.
Authentication & Security

The application should use Django authentication.

Users must only be able to see and modify:

Their own trades
Their own scripts
Their own portfolio
Their own profile information

All portfolio-related queries should be filtered by the authenticated user.

Sensitive configuration such as Django SECRET_KEY, database credentials and API-related configuration should be stored in environment variables.

Technology Stack
Backend: Django
Language: Python
Database: SQLite for development, PostgreSQL recommended for production
Market Data: yfinance
Frontend: Django Templates, HTML, CSS, JavaScript
Charts: Chart.js or another lightweight charting library
Authentication: Django Authentication
Environment Configuration: .env
Installation

Clone the project and create a virtual environment:

python -m venv venv


Activate it.

Linux/macOS
source venv/bin/activate

Windows
venv\Scripts\activate


Install dependencies:

pip install -r requirements.txt


Run migrations:

python manage.py migrate


Create an admin user:

python manage.py createsuperuser


Start the development server:

python manage.py runserver


Then open:

http://127.0.0.1:8000/

Example Workflow
Login to the application.
Create a script such as Long Term.
Add a BUY trade:
Stock: RELIANCE.NS
Quantity: 100
Price: ₹500
Date: 05 Aug 2026
Script: Long Term
Add another BUY:
Quantity: 50
Price: ₹550
Date: 13 Aug 2026
Dashboard shows:
150 shares
Average cost of ₹516.67
Add a SELL trade:
Quantity: 20
Price: ₹570
Dashboard updates the remaining position and realized P/L.
The complete BUY/SELL history remains available.
Script performance automatically includes the relevant trades.
Current market prices are refreshed separately from historical trade records.
Future Enhancements

The initial version should stay simple, but the architecture should allow future additions such as:

Broker/import support
CSV trade import
Dividend tracking
Brokerage and tax calculation
STCG/LTCG calculations
Corporate actions
Stock splits
Bonus shares
Portfolio snapshots
Multiple portfolios
Watchlist
Price alerts
Daily portfolio valuation
More advanced performance analytics
Export to CSV/Excel/PDF
Mobile-friendly PWA
Scheduled market-price updates
Benchmark comparison with NIFTY/SENSEX
Important Design Principle

The application should treat trades as the source of truth.

Instead of manually storing:

RELIANCE = 130 shares


the system should derive the holding from:

BUY  100
BUY   50
SELL  20
-----------
     130


Similarly, portfolio P/L should be calculated from the transaction history and current market prices.

This ensures that the portfolio remains auditable, every calculation can be traced back to an actual trade, and adding/editing historical transactions can correctly recalculate the portfolio.

Project Goal

The goal is to build a simple but detailed personal Indian equity portfolio management application where every trade is recorded once and the application automatically turns those trades into:

Current holdings
Average prices
Invested value
Current value
Realized P/L
Unrealized P/L
Total P/L
Stock-wise performance
Script-wise performance
Trade history
Portfolio charts

The interface should remain clean and straightforward while the backend handles the portfolio calculations accurately.

## About Dynamic Labz

Brigy is proudly built by **Dynamic Labz**, a software company focused on building custom software, automation solutions, and modern SaaS products for businesses. :contentReference[oaicite:0]{index=0}

**Website:** : https://www.dynamiclabz.net

---

## 💜 Built with love by Dynamic Labz