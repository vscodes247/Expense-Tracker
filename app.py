import requests
from flask import Flask, render_template, request
from flask_pymongo import PyMongo
from flask_wtf import FlaskForm
from pymongo import MongoClient
from wtforms import StringField, DecimalField, SelectField
from wtforms.fields.html5 import DateField
import main_functions

# Connect to database and initialize API key variables
creds = main_functions.read_from_file("JSON_Documents/credentials.json")
app = Flask(__name__)
app.debug = True
name = creds["username"]
password = creds["password"]
currency_key = creds["currency_key"]
secret_key = creds["secret_key"]
app.config["SECRET_KEY"] = f"{secret_key}"
db_url = f"mongodb+srv://{name}:{password}@mongodbpractice.8wcth.mongodb.net/mongoDBpractice?retryWrites=true&w=majority"
app.config["MONGO_URI"] = db_url
mongo = PyMongo(app)
client = MongoClient(db_url)
expense_DB = client["ExpenseDB"]
expense_col = expense_DB["Expenses"]


# Class that holds all attributes related to the form, and thus, the records to be inserted into the DB
class Expenses(FlaskForm):
    desc = StringField("Purchase Description")
    category = SelectField("Purchase Category", choices=[["rent", "Rent"], ["electricity", "Electricity"],
                                                         ["water", "Water"], ["insurance", "Insurance"],
                                                         ["groceries", "Groceries"],
                                                         ["restaurants", "Restaurants"], ["gas", "Gas"],
                                                         ["college", "College"],
                                                         ["party", "Party"], ["mortgage", "Mortgage"]])
    currency = SelectField("Currency Used", choices=[["USDUSD", "United States Dollar"],
                                                     ["USDEUR", "Euro"], ["USDJPY", "Japanese Yen"],
                                                     ["USDGBP", "British Pound"],
                                                     ["USDAUD", "Australian Dollar"],
                                                     ["USDCAD", "Canadian Dollar"],
                                                     ["USDCHF", "Swiss Franc"], ["USDCNY", "Chinese Yuan"],
                                                     ["USDSEK", "Swedish Krona"],
                                                     ["USDNZD", "New Zealand Dollar"]])
    cost = DecimalField("Cost of purchase", places=2)
    date = DateField("Date of purchase", format="%Y-%m-%d")


# Returns a list of expenses from a given category
def get_category_expenses(category):
    category_cost = 0
    find_category = {"category": f"{category}"}
    categorized_expenses = expense_col.find(find_category)
    for i in categorized_expenses:
        category_cost += float(i["cost"])
    return category_cost


# Convert cost from given currency to target currency
def currency_converter(cost, currency):
    url = f"http://api.currencylayer.com/live?access_key={currency_key}"
    response = requests.get(url).json()
    rates = response["quotes"]
    target_rate = rates[f"{currency}"]
    unrounded_cost = float(cost) / float(target_rate)
    # Round converted cost to two decimal places, as to mirror real-life currency
    converted_cost = round(unrounded_cost, 2)
    return converted_cost


@app.route('/')
# Render a view of the current expense database's totals for each category
def index():
    my_expenses = expense_col.find({}, {"cost"})
    total_cost = 0

    # Add all expenses from all categories
    for i in my_expenses:
        total_cost += float(i["cost"])
    category_list = ["rent", "electricity", "water", "insurance", "groceries",
                     "restaurants", "gas", "college", "party", "mortgage"]
    formatted_expenses = ""
    for i in category_list:
        formatted_expenses += f"You've spent a total of <b>$" + str(
            get_category_expenses(f"{i}")) + f"</b> on <b>{i}</b> <br/>"

    # when returning templates via Flask, arguments passed are in the form HTML_variable = Py_variable
    return render_template("index.html", expenses=total_cost, expensesByCategory=formatted_expenses)


@app.route('/addExpenses', methods=["GET", "POST"])
def add_expenses():
    # Include the form
    expenses_form = Expenses(request.form)
    if request.method == "POST":
        # Ensure that form elements have valid input
        if expenses_form.validate_on_submit():
            # Convert currency selected to USD
            cost = currency_converter(expenses_form.cost.data, expenses_form.currency.data)
            # Create record to add to DB
            record = {"desc": f"{expenses_form.desc._value()}", "category": f"{expenses_form.category.data}",
                      "cost": f"{cost}", "date": f"{expenses_form.date._value()}"}
            # Insert record to DB
            expense_col.insert_one(record)
            return render_template("expenseAdded.html")

    return render_template("addExpenses.html", form=expenses_form)


app.run()
