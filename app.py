from flask import Flask, render_template, url_for, redirect, session, request
import db
import security
from flask_login import login_user, LoginManager, login_required, logout_user, current_user, UserMixin
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, DecimalField, DateField, SelectField, TextAreaField, SelectMultipleField, RadioField, BooleanField
from wtforms.validators import InputRequired, Length, ValidationError, Optional, Email, EqualTo
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from wtforms.widgets import Select

import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt

import graph_budget_goals
import graph_overall
import graph_week_summary
import get_df

color_palette = {
    'purple' : '#8a3ffc',
    'pink' : '#ff7eb6',
    'green' : '#6fdc8c',
    'yellow' : 'gold',
    'orange' : '#ba4e00',
    'cyan' : '#33b1ff',
    'red' : '#fa4d56',
    'blue' : '#4589ff',
    'teal' : '#08bdba',
    'lightpurple' : '#d4bbff',
    'seafoam' : '#007d79',
    'magenta' : '#d12771',
    'lightblue' : '#bae6ff',
    'blue.darker' : '#1B3666',
    'blue.lighter': '#B4CFFF'
}

cat_colors = [
    '#8a3ffc',
    '#ff7eb6',
    '#6fdc8c',
    'gold',
    '#ba4e00',
    '#33b1ff',
    '#d4bbff',
    '#007d79',
    '#d12771',
    '#bae6ff',
]

layout_palette = {
    'black' : '#1E1E24',
    'darkgray': '#2b2b36',
    'white' : 'white',
    'lightgray' : '#3e3e52',
}

color_trans = {
    'blue': 'rgba(69, 137, 255,0.3)'
}

month_dict = {
    1: 'January',
    2: 'February',
    3: 'March',
    4: 'April',
    5: 'May',
    6: 'June',
    7: 'July',
    8: 'August',
    9: 'September',
    10:'October',
    11:'November',
    12:'December'
}

account_id = 1

server = Flask(__name__)
server.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///database.db'
server.config['SECRET_KEY'] = 'mowllmowllmowll'
alcDB = SQLAlchemy(server)
app = dash.Dash(server=server,url_base_pathname="/dashboard/")

login_manager = LoginManager()
login_manager.init_app(server)
login_manager.login_view = "login"

class User(alcDB.Model, UserMixin):
    id = alcDB.Column(alcDB.Integer, primary_key=True)
    username = alcDB.Column(alcDB.String(25), nullable=False, unique=True)

@login_manager.user_loader
def load_user(account_id):
    user_data = db.get_account(account_id=account_id)
    return User(id=user_data[0], username=user_data[1])

class RegisterForm(FlaskForm):
    username = StringField('Username',validators=[InputRequired("Please enter a username"),Length(min=4,max=25)], render_kw={"placeholder":"Username"})
    password = PasswordField('Password',validators=[InputRequired("Please enter a password"),Length(min=8,max=50)], render_kw={"placeholder":"Password"})
    confirm_password = PasswordField('Confirm Password',validators=[EqualTo(fieldname="password",message="Passwords must match"),InputRequired("Please confirm your password"),Length(min=8,max=50)], render_kw={"placeholder":"Confirm Password"})
    first_name = StringField('First Name',validators=[InputRequired("Please enter your first name"),Length(min=1,max=50)], render_kw={"placeholder":"First Name"})
    last_name = StringField('Last Name',validators=[InputRequired("Please enter your last name"),Length(min=1,max=50)], render_kw={"placeholder":"First Name"})
    email = StringField('Email',validators=[Email("This field requires a valid email address"),InputRequired("Please enter a valid email"),Length(min=4,max=50)], render_kw={"placeholder":"Email"})
    phone = StringField('Phone Number',validators=[Optional("Optional")], render_kw={"placeholder":"(   )    -     "})
    dob = DateField('Date of Birth', validators=[Optional("Optional")])
    submit = SubmitField("Sign Up")
    

class LoginForm(FlaskForm):
    username = StringField('Username',validators=[InputRequired("Please enter a username"),Length(min=4,max=25)], render_kw={"placeholder":"Username"})
    password = PasswordField('Password',validators=[InputRequired("Please enter a password"),Length(min=4,max=50)], render_kw={"placeholder":"Password"})
    submit = SubmitField("Login")

class TransactionForm(FlaskForm):
    value = DecimalField('Amount Spent', validators=[InputRequired("Please enter the amount spent")], render_kw={'placeholder':'$$$'})
    date = DateField('Date', validators=[InputRequired("Please enter the transaction date")], render_kw={'placeholder':'mm-dd-yyyy'})
    category = SelectField('Spending Category', validators=[InputRequired("Please select a category")], choices=[])
    submit = SubmitField('Add Transaction')

class SubmitAllForm(FlaskForm):
    submit_all = SubmitField("Submit")

class CategoryForm(FlaskForm):
    name = StringField('Category Name',validators=[InputRequired("Please enter a category name"),Length(min=1,max=50)], render_kw={"placeholder":"Name"})
    desc = TextAreaField('Category Description',validators=[Optional("Optional"),Length(min=1,max=120)], render_kw={"placeholder":"Description"})
    goal = SelectField('Bucket', validators=[Optional("Optional")], choices=[])
    submit = SubmitField('Add Spending Category')

class EditCategoryForm(FlaskForm):
    name = StringField('Category Name',validators=[InputRequired("Please enter a category name"),Length(min=1,max=50)], render_kw={"placeholder":"Name"})
    desc = TextAreaField('Category Description',validators=[Optional("Optional"),Length(min=1,max=120)], render_kw={"placeholder":"Description"})
    goal = SelectField('Bucket', validators=[Optional("Optional")], choices=[])
    submit = SubmitField("Apply")

class BucketForm(FlaskForm):
    bname = StringField('Bucket Name',validators=[InputRequired("Please enter a bucket name"),Length(min=1,max=50)], render_kw={"placeholder":"Name"})
    bvalue = DecimalField('Target Spending Amount', validators=[InputRequired("Please enter your target spending")], render_kw={'placeholder':'$$$'})
    bdesc = TextAreaField('Bucket Description',validators=[Optional("Optional"),Length(min=1,max=120)], render_kw={"placeholder":"Description"})
    submit = SubmitField("Add Bucket")

class EditBucketForm(FlaskForm):
    bname = StringField('Bucket Name',validators=[InputRequired("Please enter a bucket name"),Length(min=1,max=50)], render_kw={"placeholder":"Name"})
    bvalue = DecimalField('Target Spending Amount', validators=[InputRequired("Please enter your target spending")], render_kw={'placeholder':'$$$'})
    bdesc = TextAreaField('Bucket Description',validators=[Optional("Optional"),Length(min=1,max=120)], render_kw={"placeholder":"Description"})
    submit = SubmitField("Apply")

class TransactionSearchForm(FlaskForm):
    min_date = DateField('Oldest Date', validators=[Optional()], render_kw={'placeholder':'mm-dd-yyyy'})
    max_date = DateField('Newest Date', validators=[Optional()], render_kw={'placeholder':'mm-dd-yyyy'})
    categories = SelectMultipleField('Spending Category', validators=[Optional()], choices=[], widget=Select(multiple=False), default=['ALL'])
    sort_by = SelectMultipleField('Sort By', validators=[Optional()], choices=[('date','Date'),('value','Amount Spent')], widget=Select(multiple=False))
    sort_order = BooleanField('Ascending Order', default=1)
    search = SubmitField('Search')

class NewUserForm(FlaskForm):
    income = DecimalField('Disposable Income', validators=[InputRequired("Please enter disposable income")], render_kw={"placeholder":"$$$"})
    submit = SubmitField("Get Started")

@server.route('/')
def home():
    return render_template('home.html')

@server.route('/dash', methods=['GET','POST'])
@login_required
def dash():
    fname = db.get_account_name(session['account_id'])[0]
    return render_template("dash.html", fname=fname)

@server.route('/dashboard/', methods=['GET','POST'])
@login_required
def dashboard():
    return redirect(url_for("/dashboard/"))

@server.route('/enterdata', methods=['GET','POST'])
@login_required
def enterdata():
    form = TransactionForm()
    submit_form = SubmitAllForm()
    search_form = TransactionSearchForm()

    account_id = session['account_id']

    query = "SELECT transaction_category_id, transaction_category_name FROM transaction_categories WHERE account_id = ? AND transaction_category_is_active = 1;"
    cat_rows = db.select(query, [account_id])
    cat_dict = {}
    categories = []
    for row in cat_rows:
        cat_dict[row[0]] = row[1]
        cat = (row[0],row[1])
        categories.append(cat)

    form.category.choices = categories
    search_form.categories.choices = [(c[0], c[1]) for c in categories]
    search_form.categories.choices.insert(0,(-1,'ALL'))

    if f'transactions_{account_id}' not in session:
        session[f'transactions_{account_id}'] = []

    if f'search_{account_id}' not in session:
        session[f'search_{account_id}'] = []
    
    if f'latest_search_{account_id}' not in session:
        session[f'latest_search_{account_id}'] = {}   

    if f'num_results_{account_id}' not in session:
        session[f'num_results_{account_id}'] = ''     

    if request.method == "POST":
        if form.validate_on_submit() and 'new_transaction_submit' in request.form:
            transaction = {
                'value':float(form.value.data),
                'date':form.date.data.strftime('%m/%d/%Y'),
                'category':form.category.data,
                'name':cat_dict[int(form.category.data)]
            }
            session[f'transactions_{account_id}'].append(transaction)
            session.modified = True
            return redirect(url_for('enterdata')) 
        
        elif submit_form.validate_on_submit() and 'submit_all' in request.form:
            if submit_form.submit_all.data == True:
                if len(session[f'transactions_{account_id}']) > 0:
                    trans_rows = []
                    for transaction in session[f'transactions_{account_id}']:
                        trans = []
                        trans.append(account_id)
                        trans.append(float(transaction['value']))
                        trans.append(transaction['date'])
                        trans.append(int(transaction['category']))
                        trans_rows.append(trans)
                    db.bulk_insert_transaction(trans_rows)

                    session[f'transactions_{account_id}'] = []
                    return redirect(url_for('enterdata'))
                else:
                    message = "You must enter at least one transaction to submit"
                    submit_form.submit_all.errors.append(message)

        elif search_form.validate_on_submit() and 'search_transactions_submit' in request.form:
            if search_form.min_date.data == None or search_form.max_date.data == None or search_form.min_date.data <= search_form.max_date.data:
                session[f'search_{account_id}'] = []
                session[f'latest_search_{account_id}'] = {}
            

                min_date = search_form.min_date.data.strftime('%m-%d-%Y') if search_form.min_date.data else None
                max_date = search_form.max_date.data.strftime('%m-%d-%Y') if search_form.max_date.data else None
                spending_category = int(search_form.categories.data[0])
                sortby = search_form.sort_by.data[0]
                order = search_form.sort_order.data
                rows = db.search_transactions(account_id=account_id, min_date=min_date, max_date=max_date, category=spending_category, sort_by=sortby, asc=order)

                for row in rows:
                    date_obj = dt.datetime.strptime(str(row[1]), "%Y-%m-%d")
                    formatted_date = date_obj.strftime("%m/%d/%Y")

                    transaction = {
                        "id" : row[0],
                        "date" : formatted_date,
                        "value" : row[2],
                        "cat_id" : row[3],
                        "cat_name" : row[4]
                    }
                    session[f'search_{account_id}'].append(transaction)

                num_results = len(session[f'search_{account_id}'])
                if num_results >= 20:
                    session[f'num_results_{account_id}'] = "Top (" + str(num_results) + ")"
                else: 
                    session[f'num_results_{account_id}'] = "(" + str(num_results) + ")"

                session[f'latest_search_{account_id}']['min_date'] = search_form.min_date.data if search_form.min_date.data else None
                session[f'latest_search_{account_id}']['max_date'] = search_form.max_date.data if search_form.max_date.data else None
                session[f'latest_search_{account_id}']['category'] = search_form.categories.data if search_form.categories.data else None
                session[f'latest_search_{account_id}']['sort_by'] = search_form.sort_by.data if search_form.sort_by.data else None
                session[f'latest_search_{account_id}']['sort_order'] = search_form.sort_order.data if search_form.sort_order.data else None

                return redirect(url_for('enterdata'))
            
            else:
                message = "Oldest search date must be less than or equal to newest search date"
                search_form.max_date.errors.append(message)
            
        elif 'delete' in request.form:
            transaction_index = int(request.form.get('transaction_index'))
            if 0 <= transaction_index < len(session[f'transactions_{account_id}']):
                del session[f'transactions_{account_id}'][transaction_index]
                session.modified = True
            return redirect(url_for('enterdata'))
        
        elif 'confirm_delete_transaction' in request.form:
            delete_index = int(request.form.get('delete_transaction_index'))
            delete_id = session[f'search_{account_id}'][delete_index]['id']
            db.delete_transaction(delete_id)
            session[f'search_{account_id}'].pop(delete_index)
            session.modified = True
            return redirect(url_for('enterdata'))

       
    if f'latest_search_{account_id}' in session:
        if 'min_date' in session[f'latest_search_{account_id}'].keys():
            if session[f'latest_search_{account_id}']['min_date'] != None:
                search_form.min_date.data = dt.datetime.strptime(session[f'latest_search_{account_id}']['min_date'],("%a, %d %b %Y %H:%M:%S %Z"))
        if 'max_date' in session[f'latest_search_{account_id}'].keys():
            if session[f'latest_search_{account_id}']['max_date'] != None:
                search_form.max_date.data = dt.datetime.strptime(session[f'latest_search_{account_id}']['max_date'],("%a, %d %b %Y %H:%M:%S %Z"))
        if 'category' in session[f'latest_search_{account_id}'].keys():
            search_form.categories.data = session[f'latest_search_{account_id}']['category']
        if 'sort_by' in session[f'latest_search_{account_id}'].keys():
            search_form.sort_by.data = session[f'latest_search_{account_id}']['sort_by']
        if 'sort_order' in session[f'latest_search_{account_id}'].keys():
            search_form.sort_order.data = session[f'latest_search_{account_id}']['sort_order']
    

    return render_template('enterdata.html', form=form, submit_form=submit_form, transactions=session[f'transactions_{account_id}'], enumerate=enumerate, search_form=search_form, search=session[f'search_{account_id}'], num_results=session[f'num_results_{account_id}'])

@server.route('/editcategories', methods=['GET','POST'])
@login_required
def editcategories():
    account_id = session['account_id']

    new_form = CategoryForm()
    new_bucket_form = BucketForm()

    active_goals = []
    sql = 'SELECT budget_goal_name, budget_goal_id FROM budget_goals WHERE account_id = ? AND budget_goal_is_active = 1;'
    goal_rows = db.select(sql=sql, items=[account_id])
    goal_dict = {}
    for row in goal_rows:
        goal_dict[row[0]] = row[1]
        active_goals.append(row[0])


    active_goals.insert(0, None)
    new_form.goal.choices = active_goals

    session[f'categories_{account_id}'] = []
    

    sql = 'SELECT tc.transaction_category_id, tc.transaction_category_name, tc.transaction_category_desc, b.budget_goal_name FROM transaction_categories tc LEFT OUTER JOIN budget_goals b ON tc.budget_goal_id = b.budget_goal_id WHERE tc.account_id = ? AND tc.transaction_category_is_active = 1 ORDER BY tc.transaction_category_name;'
    rows = db.select(sql=sql, items=[account_id])
    for row in rows:
        c_id = row[0]
        c_name = row[1]
        c_desc = row[2]
        c_goal = row[3]
            
        category = {
            'c_id' : int(c_id),
            'c_name' : c_name,
            'c_desc' : c_desc,
            'c_goal' : c_goal
        }

        session[f'categories_{account_id}'].append(category)

    edit_forms = [EditCategoryForm(prefix=str(i)) for i in range(len(session[f'categories_{account_id}']))]
    for form in edit_forms:
        form.goal.choices = active_goals

    session[f'buckets_{account_id}'] = []

    bucket_sql = 'SELECT budget_goal_id, budget_goal_target_value, budget_goal_name, budget_goal_desc FROM budget_goals WHERE account_id = ? AND budget_goal_is_active = 1 ORDER BY budget_goal_name;'
    bucket_rows = db.select(sql=bucket_sql, items=[account_id])
    for row in bucket_rows:
        b_id = row[0]
        b_value = row[1]
        b_name = row[2]
        b_desc = row[3]

        bucket = {
            'b_id' : int(b_id),
            'b_value' : float(b_value),
            'b_name' : b_name,
            'b_desc' : b_desc
        }

        session[f'buckets_{account_id}'].append(bucket)

    bucket_edit_forms = [EditBucketForm(prefix=str(i)) for i in range(len(session[f'buckets_{account_id}']))]

    if request.method == "POST":
        if new_form.validate_on_submit() and 'new_category_form_submit' in request.form:
            new_category = {
                "account_id" : account_id,
                "name" : new_form.name.data,
                "desc" : new_form.desc.data,
                "goal" : goal_dict[new_form.goal.data] if new_form.goal.data != "None" else None
            }
            if validate_category(account_id=account_id, name=new_category['name']):
                db.insert_transaction_category(items=[new_category['account_id'],new_category['name']],budget_goal=new_category['goal'],desc=new_category['desc'])
                return redirect(url_for('editcategories'))
            else:
                message = "You cannot create two spending categories with the same name"
                new_form.name.errors.append(message)
        elif 'confirm_delete' in request.form:
            category_index = int(request.form.get('category_index'))
            delete_id = session[f'categories_{account_id}'][category_index]['c_id']
            transfer_name = request.form.get('transfer_category')
            transfer_index = None
            for i, cat in enumerate(session[f'categories_{account_id}']):
                if cat['c_name'] == transfer_name:
                    transfer_index = i
            transfer_id = session[f'categories_{account_id}'][transfer_index]['c_id']

            db.delete_transaction_category(id=delete_id, inherit_category_id=transfer_id)
            return redirect(url_for('editcategories'))
        elif new_bucket_form.validate_on_submit() and 'new_bucket_form_submit' in request.form:
            new_bucket = {
                "account_id" : account_id,
                "name" : new_bucket_form.bname.data,
                "value" : new_bucket_form.bvalue.data,
                "desc" : new_bucket_form.bdesc.data
            }
            if validate_bucket(account_id=account_id, name=new_bucket['name']):
                db.insert_budget_goal(items=[new_bucket['account_id'],new_bucket['value'],new_bucket['name']], desc=new_bucket['desc'])
                return redirect(url_for('editcategories'))
            else:
                message = "You cannot create two buckets with the same name"
                new_bucket_form.bname.errors.append(message)
        elif 'bucket_confirm_delete' in request.form:
            bucket_index = int(request.form.get('bucket_index'))
            delete_id = session[f'buckets_{account_id}'][bucket_index]['b_id']
            transfer_name = request.form.get('transfer_bucket')
            transfer_index = None
            transfer_id = None
            for i, bucket in enumerate(session[f'buckets_{account_id}']):
                if bucket['b_name'] == transfer_name:
                    transfer_index = i
            if transfer_index != None:
                transfer_id = session[f'buckets_{account_id}'][transfer_index]['b_id']

            db.delete_budget_goal(id=delete_id, inherit_goal_id=transfer_id)
            return redirect(url_for('editcategories'))
        
    for i, edit_form in enumerate(edit_forms):
        if edit_form.validate_on_submit():
            if edit_form.submit.data == True:
                category_index = int(request.form.get('category_index'))
                cat_id = session[f'categories_{account_id}'][category_index]['c_id']
                update_sql = 'UPDATE transaction_categories SET transaction_category_name = ?, transaction_category_desc = ?, budget_goal_id = ? WHERE transaction_category_id = ?;'   
                db.update(sql=update_sql, items=[edit_form.name.data, edit_form.desc.data, goal_dict[edit_form.goal.data] if edit_form.goal.data != "None" else None, cat_id])
                return redirect(url_for('editcategories'))
        
        edit_form.name.data = session[f'categories_{account_id}'][i]['c_name']
        edit_form.desc.data = session[f'categories_{account_id}'][i]['c_desc']
        edit_form.goal.data = session[f'categories_{account_id}'][i]['c_goal']

    for i, edit_form in enumerate(bucket_edit_forms):
        if edit_form.validate_on_submit():
            if edit_form.submit.data == True:
                bucket_index = int(request.form.get('bucket_index'))
                bucket_id = session[f'buckets_{account_id}'][bucket_index]['b_id']
                update_sql = 'UPDATE budget_goals SET budget_goal_name = ?, budget_goal_desc = ?, budget_goal_target_value = ? WHERE budget_goal_id = ?;'
                db.update(sql=update_sql, items=[edit_form.bname.data, edit_form.bdesc.data, edit_form.bvalue.data, bucket_id])
                return redirect(url_for('editcategories'))
        
        edit_form.bname.data = session[f'buckets_{account_id}'][i]['b_name']
        edit_form.bdesc.data = session[f'buckets_{account_id}'][i]['b_desc']
        edit_form.bvalue.data = session[f'buckets_{account_id}'][i]['b_value']


    return render_template('editcategories.html', categories=session[f'categories_{account_id}'], enumerate=enumerate, new_form=new_form, edit_forms=edit_forms, buckets=session[f'buckets_{account_id}'], bucket_edit_forms=bucket_edit_forms, bucket_form=new_bucket_form)

@server.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        account_id = security.verify_account(form.username.data, form.password.data)
        if account_id > 0:
            new_user = db.check_new_user(account_id=account_id)

            user_data = db.get_account(account_id)
            user = User(id=user_data[0], username=user_data[1])
            login_user(user, force=True)
            session['account_id'] = current_user.id

            update_login_time = 'UPDATE accounts SET LAST_LOGIN_DATE = GETDATE() WHERE account_id = ?;'
            db.update(update_login_time, [account_id])

            if new_user:
                return redirect(url_for('new_user'))
            else:
                return redirect(url_for('dash'))
        else:
            message = "Username or password is incorrect"
            form.password.errors.append(message)

    return render_template('login.html', form=form)

@server.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@server.route('/new_user', methods=['GET','POST'])
@login_required
def new_user():
    account_id = session['account_id']
    form = NewUserForm()

    if form.validate_on_submit():
        income = form.income.data
        db.update_starter(account_id=account_id, income=income)

        return redirect(url_for('dash'))

    return render_template('new_user.html', form=form)

@server.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()

    message =""

    if form.validate_on_submit():
        if validate_username(form.username.data):
            if validate_email(form.email.data):
                items = [form.username.data, form.password.data, form.first_name.data, form.last_name.data, form.email.data]
                db.insert_account(items=items, phone=form.phone.data if form.phone.data else None, dob=form.dob.data if form.dob.data else None)
                account_id = db.get_account_id(username=form.username.data)
                db.fill_starter(account_id=account_id)
                return redirect(url_for('login'))
            else:
                message = "Already an existing account with that email"
                form.email.errors.append(message)
        else:
            message = "Username already taken. Try another."
            form.username.errors.append(message)

    return render_template('register.html', form=form)

def validate_username(username):
    sql = "SELECT account_username FROM accounts WHERE account_username = ?"
    rows = db.select(sql=sql, items=[str(username)])

    if rows:
        return 0
    else: return 1

def validate_email(email):
    sql = "SELECT account_email FROM accounts WHERE account_email = ?"
    rows = db.select(sql=sql, items=[str(email)])

    if rows:
        return 0
    else: return 1

def validate_category(account_id, name):
    sql = "SELECT transaction_category_name FROM transaction_categories WHERE account_id = ? AND transaction_category_name = ? AND transaction_category_is_active = 1;"
    rows = db.select(sql=sql, items=[account_id, name])

    if rows:
        return 0
    else: return 1

def validate_bucket(account_id, name):
    sql = "SELECT budget_goal_name FROM budget_goals WHERE account_id = ? AND budget_goal_name = ? AND budget_goal_is_active = 1;"
    rows = db.select(sql=sql, items=[account_id, name])

    if rows:
        return 0
    else: return 1


# DASH

start_account_id = 1 #for base loading, should be a valid account id

years, months = get_df.get_years_months_list(account_id=start_account_id)
now = dt.datetime.now()
current_month = now.month
current_year = now.year

app.layout = html.Div([
    html.Div([
        dcc.Store(id='months', data=months),
        dcc.Store(id='years', data=years),
        html.Button('Home', id='return_home'),
        html.H1("budge",className='title'),
        dcc.Location(id='url', refresh=True)
    ],style={'height':'10vh','background-color':layout_palette['darkgray'],'display':'flex','align-items': 'center','justify-content': 'center','position': 'relative'}),
    html.Div([
        html.Div([
            html.Label("Month", className='text2'),
            dcc.Dropdown(id='month_dropdown', clearable=False,
                #options=[{'label' : month_dict[i], 'value' : i} for i in months],
                value=current_month,className='dropdown'),
            html.Label("Year", className='text2'),
            dcc.Dropdown(id='year_dropdown', clearable=False,
                #options=[{'label' : i, 'value' : i} for i in years],
                value=current_year,className='dropdown'),
            html.H6("Latest Transaction Date:", className='text3'),
            html.H6(id='latest_date', children= str(dt.datetime.strptime(str(db.latest_transaction_date(account_id=start_account_id)), '%Y-%m-%d').strftime('%b, %d %Y')) if db.latest_transaction_date(account_id=start_account_id) else "No Transaction Data", className='text4')
        ], style={'width':'15%','margin':'20px'}),
        dcc.Graph(id='goals_graph',style={'width':'85%','height':"100%",'margin-right':'10px'},className='plot')
    ], style={'height':'45vh','display':'flex','background-color':layout_palette['black']}),
    html.Div([
        dcc.Graph(id='overall_graph',style={'width':'25%'},className='plot'),
        dcc.Graph(id='week_summary_graph',style={'width':'75%','margin-right':'10px'},className='plot')
    ], style={'height':'45vh','display':'flex','margin-bottom':'10px'})
],style={'background-color':layout_palette['black'],'width':'100%','height':'100vh'})



@app.callback(
    Output('goals_graph','figure'),
    [Input('month_dropdown','value'),
    Input('year_dropdown','value')]
)
def update_graph(selected_month, selected_year):
    df = get_df.generate_budget_goals_df(account_id=session['account_id'], year=selected_year if selected_year else current_year, month=selected_month if selected_month else current_month)

    g_fig = graph_budget_goals.gen(df, color_palette, layout_palette)

    return g_fig

@app.callback(
    Output(component_id='overall_graph',component_property='figure'),
    [Input(component_id='month_dropdown',component_property='value'),
    Input(component_id='year_dropdown',component_property='value')]
)
def update_graph(selected_month, selected_year):
    print("Updating graphs with account ID: " + str(session['account_id']))
    df = get_df.generate_budget_goals_df(account_id=session['account_id'], year=selected_year if selected_year else current_year, month=selected_month if selected_month else current_month)

    p_fig = graph_overall.gen(df, color_palette, layout_palette, color_trans)

    return p_fig

@app.callback(
    Output(component_id='week_summary_graph',component_property='figure'),
    [Input(component_id='month_dropdown',component_property='value'),
    Input(component_id='year_dropdown',component_property='value')]
)
def update_graph(selected_month, selected_year):
    w_df = get_df.generate_weekly_df(account_id=session['account_id'], year=selected_year if selected_year else current_year, month=selected_month if selected_month else current_month)

    w_fig = graph_week_summary.gen(w_df, selected_month, color_palette, layout_palette, cat_colors, month_dict)

    return w_fig

@app.callback(
    Output("month_dropdown", "options"),
    [Input('months','data')]
)
def update_months(months_def):
    years, months = get_df.get_years_months_list(account_id=session['account_id'])
    if len(months) == 0: months.append(current_month)
    months.sort()
    return [{'label' : month_dict[i], 'value' : i} for i in months]

@app.callback(
    Output("year_dropdown", "options"),
    [Input('years','data')]
)
def update_years(years_def):
    years, months = get_df.get_years_months_list(account_id=session['account_id'])
    if len(years) == 0: years.append(current_year)
    years.sort()
    return [{'label' : i, 'value' : i} for i in years]

@app.callback(
    Output("latest_date","children"),
    [Input('months','data')]
)
def update_latest_date(months):
    date = db.latest_transaction_date(account_id=session['account_id'])
    if not date:
        return 'No Transactions Entered'
    else: return str(dt.datetime.strptime(str(date), '%Y-%m-%d').strftime('%b, %d %Y'))

@app.callback(
    Output('url', 'href'),
    Input('return_home', 'n_clicks')
)
def redirect_to_home(n_clicks):
    if n_clicks is None:
        return None
    else:
        return '/dash'



if __name__ == '__main__':
    from waitress import serve
    #server.run()
    serve(app=server, host="0.0.0.0", port=8080)

