from flask import Flask, request, render_template
from decimal import Decimal, getcontext, ROUND_HALF_UP
import math
import sys
import logging
from logging.handlers import RotatingFileHandler
import requests
from datetime import datetime
from zoneinfo import ZoneInfo  # Added for timezone handling
import os  # Added for environment variables

app = Flask(__name__)

# Set decimal precision higher to handle financial calculations accurately
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_UP

# Configure Error Logging
handler = RotatingFileHandler('error.log', maxBytes=100000, backupCount=3)
handler.setLevel(logging.ERROR)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Configure Access Logging
access_handler = RotatingFileHandler('access.log', maxBytes=100000, backupCount=3)
access_handler.setLevel(logging.INFO)
access_formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s'
)
access_handler.setFormatter(access_formatter)
access_logger = logging.getLogger('access_logger')
access_logger.setLevel(logging.INFO)
access_logger.addHandler(access_handler)

# Define Central Time Zone (handles CST and CDT automatically)
CENTRAL_TIMEZONE = ZoneInfo("America/Chicago")


# Helper function to get IP info
def get_ip_info(ip_address):
    token = os.getenv('IPINFO_TOKEN', 'c3ac132bf5e169')  # Use environment variable
    url = f'https://ipinfo.io/{ip_address}/json?token={token}'
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        city = data.get('city', 'Unknown')
        region = data.get('region', 'Unknown')  # 'region' typically corresponds to state
        return city, region
    except requests.RequestException as e:
        app.logger.error(f"Error fetching IP info for {ip_address}: {e}")
        return 'Unknown', 'Unknown'

# Log IP info before each request
@app.before_request
def log_request_info():
    # Get the user's IP address
    if request.headers.getlist("X-Forwarded-For"):
        ip_address = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        ip_address = request.remote_addr or 'Unidentified IP'

    # Get city and state from IP
    city, state = get_ip_info(ip_address)

    # Get current date and time
# Get current date and time in UTC
    access_time = datetime.now(CENTRAL_TIMEZONE).strftime('%Y-%m-%d %H:%M:%S %Z')

    # Log the information
    access_logger.info(f"IP: {ip_address}, City: {city}, State: {state}, Access Time: {access_time}")

# ... [rest of your existing code remains unchanged] ...

# Your existing helper functions, routes, etc.

if __name__ == '__main__':
    # Disable debug mode in production
    app.run(debug=False)


# Set decimal precision higher to handle financial calculations accurately
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_UP

# Configure Logging
handler = RotatingFileHandler('error.log', maxBytes=100000, backupCount=3)
handler.setLevel(logging.ERROR)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
)
handler.setFormatter(formatter)
app.logger.addHandler(handler)


# Helper function for Debt Payoff Calculator
def calculate_debt_amortization_schedule(debt):
    balance = Decimal(debt['balance'])
    annual_interest_rate = Decimal(debt['interest_rate']) / Decimal('100.0')
    monthly_interest_rate = annual_interest_rate / Decimal('12.0')
    min_payment = Decimal(debt['min_payment'])
    extra_payment = Decimal(debt['extra_payment'])
    total_payment = min_payment + extra_payment

    schedule = []
    month = 1
    original_months = 0  # Initialize for original payoff period without extra payment
    original_balance = balance  # Save the original balance for later comparison

    # First, calculate the payoff period without extra payments
    while balance > 0 and month < 1000:
        interest_paid = (balance * monthly_interest_rate).quantize(Decimal('0.01'))
        principal_paid = (min_payment - interest_paid).quantize(Decimal('0.01'))

        if principal_paid <= 0:
            break  # Avoid infinite loop

        if principal_paid > balance:
            principal_paid = balance

        balance -= principal_paid
        balance = balance.quantize(Decimal('0.01'))

        if balance <= 0:
            original_months = month  # Store the original months until payoff without extra payment
            break

        month += 1

    # Now, reset the balance and calculate the schedule with extra payments
    balance = original_balance
    schedule.clear()  # Clear any previous schedule data
    month = 1
    while balance > 0 and month < 1000:
        interest_paid = (balance * monthly_interest_rate).quantize(Decimal('0.01'))
        principal_paid = (total_payment - interest_paid).quantize(Decimal('0.01'))

        if principal_paid <= 0:
            raise ValueError(f"Payment is too low to cover the interest on {debt['debt_name']}.")

        if principal_paid > balance:
            principal_paid = balance
            total_payment = principal_paid + interest_paid

        balance -= principal_paid
        balance = balance.quantize(Decimal('0.01'))

        schedule.append({
            'Month': month,
            'Payment': f"{total_payment:,.2f}",
            'Interest Paid': f"{interest_paid:,.2f}",
            'Principal Paid': f"{principal_paid:,.2f}",
            'Remaining Balance': f"{max(balance, Decimal('0.00')):,.2f}"
        })

        if balance <= 0:
            break

        month += 1

    # Calculate the early payoff savings
    early_payoff_savings = original_months - (month - 1)

    return {
        'schedule': schedule,
        'original_months': original_months,
        'original_years': math.ceil(original_months / 12),
        'months_until_payoff': month - 1,
        'years_until_payoff': math.ceil((month - 1) / 12),
        'early_payoff_savings': early_payoff_savings
    }


# Updated helper function for Mortgage Calculator
def compute_mortgage_amortization_schedule(balance, monthly_interest_rate, monthly_pay, escrow, extra_fees=Decimal('0.00'), extra_payment=Decimal('0.00')):
    schedule = []
    month = 1
    total_interest = Decimal('0.00')

    # Total payment includes monthly_pay (P&I + Escrow), extra fees, and extra payment
    total_payment = monthly_pay + extra_fees + extra_payment

    while balance > 0 and month <= 1000:
        # Calculate interest for the current month
        interest = (balance * monthly_interest_rate).quantize(Decimal('0.01'))

        # Calculate principal
        principal = (monthly_pay - interest - escrow + extra_payment).quantize(Decimal('0.01'))

        if principal <= 0:
            raise ValueError("Monthly Pay is too low to cover the interest and escrow.")

        if principal > balance:
            principal = balance
            # Adjust total payment for the last payment
            total_payment = (principal + interest + escrow + extra_fees).quantize(Decimal('0.01'))

        # Update balance
        balance -= principal
        balance = balance.quantize(Decimal('0.01'))
        total_interest += interest

        # Append monthly details to schedule
        schedule.append({
            'Month': month,
            'Payment': f"{total_payment:,.2f}",
            'Interest': f"{interest:,.2f}",
            'Principal': f"{principal:,.2f}",
            'Escrow': f"{escrow:,.2f}",
            'Extra Fees': f"{extra_fees:,.2f}" if extra_fees > 0 else '',
            'Extra Payment': f"{extra_payment:,.2f}" if extra_payment > 0 else '',
            'Remaining Balance': f"{max(balance, Decimal('0.00')):,.2f}"
        })
        month += 1

    if month > 1000:
        raise ValueError("Calculation exceeded 1000 months. Please check your inputs.")

    return schedule, total_interest, month - 1


# Route for Debt Payoff Calculator
@app.route('/', methods=['GET', 'POST'])
def debt_calculator():
    if request.method == 'POST':
        try:
            # Retrieve form data
            debt_names = request.form.getlist('debt_name[]')
            balances = request.form.getlist('balance[]')
            interest_rates = request.form.getlist('interest_rate[]')
            min_payments = request.form.getlist('min_payment[]')
            extra_payments = request.form.getlist('extra_payment[]')
            selected_currency = request.form.get('currency', 'usd')

            results = []
            errors = {}

            for i in range(len(debt_names)):
                # Extract and process inputs
                debt_name = debt_names[i].strip() or f"Debt {i+1}"
                balance_input = balances[i].strip()
                interest_rate_input = interest_rates[i].strip()
                min_payment_input = min_payments[i].strip()
                extra_payment_input = extra_payments[i].strip()

                # Convert inputs to Decimal, handle empty fields
                balance = Decimal(balance_input) if balance_input else Decimal('0.00')
                interest_rate = Decimal(interest_rate_input) if interest_rate_input else Decimal('0.00')
                min_payment = Decimal(min_payment_input) if min_payment_input else Decimal('0.00')
                extra_payment = Decimal(extra_payment_input) if extra_payment_input else Decimal('0.00')

                # Validate inputs
                if balance < 0:
                    raise ValueError("Balance cannot be negative.")
                if interest_rate < 0:
                    raise ValueError("Interest rate cannot be negative.")
                if min_payment < 0:
                    raise ValueError("Minimum payment cannot be negative.")
                if extra_payment < 0:
                    raise ValueError("Extra payment cannot be negative.")

                debt_info = {
                    'debt_name': debt_name,
                    'balance': balance,
                    'interest_rate': interest_rate,
                    'min_payment': min_payment,
                    'extra_payment': extra_payment
                }

                # Calculate amortization schedule
                result = calculate_debt_amortization_schedule(debt_info)

                # Assign the result variables and format them
                results.append({
                    'debt_name': debt_info['debt_name'],
                    'balance': f"{balance:,.2f}",
                    'interest_rate': f"{interest_rate:.2f}",
                    'min_payment': f"{min_payment:,.2f}",
                    'extra_payment': f"{extra_payment:,.2f}",
                    'schedule': result['schedule'],
                    'original_months': result['original_months'],
                    'original_years': result['original_years'],
                    'months_until_payoff': result['months_until_payoff'],
                    'years_until_payoff': result['years_until_payoff'],
                    'early_payoff_savings': result['early_payoff_savings']
                })

        except ValueError as ve:
            # Handle errors that occur in the try block
            debt_key = debt_names[i] if debt_names[i] else f"Debt {i+1}"
            errors[debt_key] = str(ve)

        except Exception as e:
            # Handle all other exceptions
            debt_key = debt_names[i] if debt_names[i] else f"Debt {i+1}"
            errors[debt_key] = f"An unexpected error occurred: {str(e)}"

        # Render the template with results and errors
        return render_template('index.html', debt_names=debt_names, balances=balances,
                               interest_rates=interest_rates, min_payments=min_payments,
                               extra_payments=extra_payments, results=results, errors=errors,
                               selected_currency=selected_currency)
    else:
        # GET request
        selected_currency = 'usd'
        # Initialize empty lists
        debt_names = []
        balances = []
        interest_rates = []
        min_payments = []
        extra_payments = []
        results = []
        errors = {}

        return render_template('index.html', debt_names=debt_names, balances=balances,
                               interest_rates=interest_rates, min_payments=min_payments,
                               extra_payments=extra_payments, results=results, errors=errors,
                               selected_currency=selected_currency)



# Updated Route for Mortgage Calculator
@app.route('/mortgage', methods=['GET', 'POST'])
def mortgage_calculator():
    if request.method == 'POST':
        try:
            # Get form data
            loan_amount_input = request.form.get('loan_amount', '').replace(',', '').strip()
            monthly_pay_input = request.form.get('monthly_pay', '').replace(',', '').strip()
            annual_rate_input = request.form.get('annual_rate', '').strip()
            term_years_input = request.form.get('term_years', '').strip()
            escrow_input = request.form.get('escrow', '').replace(',', '').strip()
            extra_fees_input = request.form.get('extra_fees', '').replace(',', '').strip()
            extra_payment_input = request.form.get('extra_payment', '').replace(',', '').strip()

            # Convert inputs to Decimal, handle empty inputs
            loan_amount = Decimal(loan_amount_input) if loan_amount_input else Decimal('0.00')
            monthly_pay = Decimal(monthly_pay_input) if monthly_pay_input else Decimal('0.00')
            annual_rate = Decimal(annual_rate_input) if annual_rate_input else Decimal('0.00')
            term_years = Decimal(term_years_input) if term_years_input else Decimal('0.00')
            escrow = Decimal(escrow_input) if escrow_input else Decimal('0.00')
            extra_fees = Decimal(extra_fees_input) if extra_fees_input else Decimal('0.00')
            extra_payment = Decimal(extra_payment_input) if extra_payment_input else Decimal('0.00')

            # Validate inputs
            if loan_amount <= 0:
                raise ValueError("Loan Amount must be greater than zero.")
            if term_years <= 0:
                raise ValueError("Term (Years) must be greater than zero.")
            if annual_rate < 0:
                raise ValueError("Annual Rate cannot be negative.")
            if escrow < 0:
                raise ValueError("Escrow cannot be negative.")
            if extra_fees < 0:
                raise ValueError("Extra Fees cannot be negative.")
            if extra_payment < 0:
                raise ValueError("Extra Payment cannot be negative.")
            if monthly_pay <= 0:
                raise ValueError("Monthly Pay must be greater than zero.")

            # Compute monthly interest rate
            monthly_interest_rate = (annual_rate / Decimal('100.0')) / Decimal('12.0')

            # Total number of payments
            total_payments = int(term_years * Decimal('12.0'))

            # Compute the principal and interest payment based on input monthly pay
            required_p_and_i = (monthly_pay - escrow).quantize(Decimal('0.01'))
            required_monthly_payment = monthly_pay  # As per your input

            # Validate that required_p_and_i is sufficient to cover interest
            # Calculate the minimum required P&I payment using the mortgage formula
            if monthly_interest_rate == 0:
                min_required_p_and_i = (loan_amount / Decimal(total_payments)).quantize(Decimal('0.01'))
            else:
                one_plus_r = Decimal('1.0') + monthly_interest_rate
                one_plus_r_pow_n = one_plus_r ** Decimal(total_payments)
                numerator = monthly_interest_rate * one_plus_r_pow_n
                denominator = one_plus_r_pow_n - Decimal('1.0')
                min_required_p_and_i = (loan_amount * numerator / denominator).quantize(Decimal('0.01'))

            if required_p_and_i < min_required_p_and_i:
                raise ValueError(f"Your Principal & Interest Payment (${required_p_and_i:,.2f}) is less than the minimum required payment (${min_required_p_and_i:,.2f}) to amortize the loan over {term_years} years.")

            # Compute amortization schedule WITHOUT extra payment
            schedule_without_extra, total_interest_without_extra, months_until_payoff_without_extra = compute_mortgage_amortization_schedule(
                loan_amount, monthly_interest_rate, monthly_pay, escrow, extra_fees, extra_payment=Decimal('0.00')
            )

            # Compute amortization schedule WITH extra payment
            schedule_with_extra, total_interest_with_extra, months_until_payoff_with_extra = compute_mortgage_amortization_schedule(
                loan_amount, monthly_interest_rate, monthly_pay, escrow, extra_fees, extra_payment
            )

            # Calculate years until payoff
            years_until_payoff_without_extra = months_until_payoff_without_extra // 12
            years_until_payoff_with_extra = months_until_payoff_with_extra // 12

            # Calculate early payoff savings
            early_payoff_savings = months_until_payoff_without_extra - months_until_payoff_with_extra

            # Prepare results to send to the template
            results = {
                'loan_amount': f"{loan_amount:,.2f}",
                'monthly_pay': f"{monthly_pay:,.2f}",
                'annual_rate': f"{annual_rate:.3f}",
                'term_years': f"{term_years}",
                'escrow': f"{escrow:,.2f}",
                'extra_fees': f"{extra_fees:,.2f}",
                'extra_payment': f"{extra_payment:,.2f}",
                'required_p_and_i': f"{required_p_and_i:,.2f}",
                'required_monthly_payment': f"{required_monthly_payment:,.2f}",
                'total_interest': f"{total_interest_with_extra:,.2f}",
                'months_until_payoff': months_until_payoff_with_extra,
                'years_until_payoff': years_until_payoff_with_extra,
                'months_until_payoff_without_extra': months_until_payoff_without_extra,
                'years_until_payoff_without_extra': years_until_payoff_without_extra,
                'early_payoff_savings': early_payoff_savings,
                'schedule': schedule_with_extra
            }

            return render_template('mortgage.html', results=results)
        except ValueError as ve:
            error_message = str(ve)
            app.logger.error(f"ValueError in mortgage_calculator: {ve}")
            return render_template('mortgage.html', error_message=error_message, form_data=request.form), 400
        except Exception as e:
            # Log the exception with traceback
            app.logger.error("Unhandled Exception in mortgage_calculator", exc_info=e)
            return render_template('mortgage.html', error_message="An unexpected error occurred.", form_data=request.form), 500
    else:
        # GET request
        return render_template('mortgage.html')


if __name__ == '__main__':
    # Disable debug mode in production
    app.run(debug=False)
