import pypyodbc as odbc
import security
import hashlib
from queue import Queue

from dotenv import load_dotenv
import os

load_dotenv()

username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
server_name = os.getenv('DB_HOST')
db_name = os.getenv('DB_NAME')

local_connection_string = 'Driver={ODBC Driver 13 for SQL Server};Server=localhost;Database=Budge;Trusted_Connection=yes;TrustServerCertificate=yes;'
db_connection_string = 'Driver={ODBC Driver 13 for SQL Server};Server=tcp:'+server_name+',1433;Database='+db_name+';Uid='+username+';Pwd='+password+';Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

connection_string = local_connection_string

class ConnectionPool:
    def __init__(self, max_connections, connection_string):
        self.connection_string = connection_string
        self.pool = Queue(maxsize=max_connections)
        for _ in range(max_connections):
            self.pool.put(self._create_new_connection())

    def _create_new_connection(self):
        return odbc.connect(self.connection_string)

    def get_connection(self):
        return self.pool.get()

    def return_connection(self, connection):
        self.pool.put(connection)

    def close_all_connections(self):
        while not self.pool.empty():
            connection = self.pool.get()
            connection.close()

pool = ConnectionPool(max_connections=5, connection_string=connection_string)

# Connects to Budge DB, returning a connection and cursor object
def connect():
    try: 
        conn = pool.get_connection()
        cursor = conn.cursor()
        return conn, cursor
    except:
        raise ConnectionError

# Takes in connection object and closes connection
def disconnect(conn):
    try:
        pool.return_connection(conn)
    except:
        raise ConnectionError

# generic sql insert statment - takes sql string and list of items to insert
def insert(sql, items):
    args = tuple(items)

    conn, cursor = connect()

    cursor.execute(sql, args)
    conn.commit()

    disconnect(conn)

# generic sql select statement - takes sql string and list of items in case of WHERE
def select(sql, items):
    args = tuple(items)

    conn, cursor = connect()

    cursor.execute(sql, args)
    rows = cursor.fetchall()

    disconnect(conn)
    return rows

# generic sql update statement - takes sql string and list of update criteria
def update(sql, items):
    args = tuple(items)

    conn, cursor = connect()

    cursor.execute(sql, args)
    conn.commit()

    disconnect(conn)

# inserts a new account item - takes a list of required attributes (username, password, first_name, last_name, email)
# optionally takes phone str and dob str
def insert_account(items, phone=None, dob=None):
    # generates password salt
    salt = security.generate_salt()

    # instantiate hasher and hash concat salt + password
    hasher = hashlib.sha256()

    hasher.update(salt + items[1].encode())

    # put new hashed password into account info list and then add phone, dob, and salt
    items[1] = hasher.hexdigest()

    items.append(phone)
    items.append(dob)
    items.insert(2, salt.hex())

    # insert the account info
    sql = 'INSERT INTO accounts (account_username, account_password_hash, account_password_salt, account_first_name, account_last_name, account_email, account_phone, account_date_of_birth) VALUES (?, ?, ?, ?, ?, ?, ?, ?);'
    insert(sql=sql, items=items)

# inserts a new budget goal item - takes a list of required attributes (account_id, budget_goal_target_value, budget_goal_name)
# optionally takes budget_goal_desc str
def insert_budget_goal(items, desc=None):
    items.append(desc)

    sql = 'INSERT INTO budget_goals (account_id, budget_goal_target_value, budget_goal_name, budget_goal_desc) VALUES (?, ?, ?, ?);'
    insert(sql=sql, items=items)

# returns true if the budget_goal at id is active
def check_active_budget_goal(id):
    check = select('SELECT * FROM budget_goals WHERE budget_goal_id = ? AND budget_goal_is_active = 1;', [id])

    if check: return True
    else: return False   

# inserts a new transaction category item - takes a list of required attributes (account_id, transaction_category_name)
# optionally takes a budget_goal and transaction_category_desc
def insert_transaction_category(items, budget_goal=None, desc=None):
    items.append(budget_goal)
    items.append(desc)

    sql = 'INSERT INTO transaction_categories (account_id, transaction_category_name, budget_goal_id, transaction_category_desc) VALUES (?, ?, ?, ?);'
    insert(sql=sql, items=items)
    
# returns True if transaction_category at id is active
def check_active_transaction_category(id):
    check = select('SELECT * FROM transaction_categories WHERE transaction_category_id = ? AND transaction_category_is_active = 1;', [id])

    if check: return True
    else: return False

# inserts a new transaction item - takes a list of required attributes (account_id, transaction_value, transaction_date, transaction_category_id)
def insert_transaction(items):
    sql = 'INSERT INTO transactions (account_id, transaction_value, transaction_date, transaction_category_id) VALUES (?, ?, ?, ?);'
    insert(sql=sql, items=items)

# for bulk inserting transactions. We only connect once, build a bulk connection query and then run it and disconnect. It's faster.
# takes in a list of rows, with each row containing the four required attributes of a transaction (account_id, transaction_value, transaction_date, transaction_category_id))
def bulk_insert_transaction(rows):
    items = []

    sql = 'INSERT INTO transactions (account_id, transaction_value, transaction_date, transaction_category_id) VALUES '

    conn, cursor = connect()

    for row in rows:
        check_sql = 'SELECT * FROM transaction_categories WHERE transaction_category_id = ? AND transaction_category_is_active = 1'
        cursor.execute(check_sql, (row[3],))
        check = cursor.fetchall()

        if check:
            sql = sql + '(?, ?, ?, ?),'

            for item in row:
                items.append(item)
        else:
            disconnect(conn)
            raise ValueError('Cannot insert transaction: Transaction category with id [' + str(row[3]) + '] is inactive')

    # remove last comma and add semi colon
    sql = sql[:-1]
    sql = sql + ';'

    args = tuple(items)

    cursor.execute(sql, args)
    conn.commit()

    disconnect(conn)

# sets inactive
# takes in the table name and the primary key id of the row to update
def set_inactive(table_name, id):
    bit = 0
    
    update_col = ''
    if table_name == 'accounts': update_col = 'account_is_active'
    elif table_name == 'budget_goals': update_col = 'budget_goal_is_active'
    elif table_name == 'transaction_categories': update_col = 'transaction_category_is_active'
    elif table_name == 'transactions': update_col = 'transaction_is_active'

    id_col = ''
    if table_name == 'accounts': id_col = 'account_id'
    elif table_name == 'budget_goals': id_col = 'budget_goal_id'
    elif table_name == 'transaction_categories': id_col = 'transaction_category_id'
    elif table_name == 'transactions': id_col = 'transaction_id'

    items = [bit, id]

    sql = 'UPDATE '+table_name+' SET '+update_col+' = ? WHERE '+id_col+' = ?;'
    update(sql=sql, items=items)

# proper function to set a budget goal inactive. Reassigns all categories dependent to null
def delete_budget_goal(id, inherit_goal_id=None):
    conn, cursor = connect()

    cat_sql = 'SELECT transaction_category_id FROM transaction_categories WHERE budget_goal_id = ? AND transaction_category_is_active = 1;'
    cursor.execute(cat_sql, (id,))

    rows = cursor.fetchall()

    if rows:
        update_cat_sql = 'UPDATE transaction_categories SET budget_goal_id = ? WHERE transaction_category_id = ?;'
    
        for row in rows:
            cursor.execute(update_cat_sql, (inherit_goal_id,row[0]))

    update_sql = 'UPDATE budget_goals SET budget_goal_is_active = 0 WHERE budget_goal_id = ?;'
    cursor.execute(update_sql, (id,))

    conn.commit()
    disconnect(conn)

# proper function to set transaction category inactive. Reassigns all transactions to the mandatory inherit category param
def delete_transaction_category(id, inherit_category_id):
    conn, cursor = connect()

    cat_sql = 'SELECT transaction_id FROM transactions WHERE transaction_category_id = ? AND transaction_is_active = 1;'
    cursor.execute(cat_sql, (id,))

    rows = cursor.fetchall()

    if rows:
        update_trans_sql = 'UPDATE transactions SET transaction_category_id = ? WHERE transaction_id = ?;'
    
        for row in rows:
            cursor.execute(update_trans_sql, (inherit_category_id,row[0]))

    update_sql = 'UPDATE transaction_categories SET transaction_category_is_active = 0 WHERE transaction_category_id = ?;'
    cursor.execute(update_sql, (id,))

    conn.commit()
    disconnect(conn)

def delete_transaction(id):
    sql = "UPDATE transactions SET transaction_is_active = 0 WHERE transaction_id = ?;"
    update(sql=sql, items=[id])

# returns the first and last name of the account taking in an account id
def get_account_name(account_id):
    # defining the sql queries for getting the data
    account_sql = 'SELECT account_first_name, account_last_name FROM accounts WHERE account_id = ? AND account_is_active = 1;'

    # connect to db and execute queries, extracting information
    conn, cursor = connect()

    first_name = ''
    last_name = ''
    cursor.execute(account_sql, (account_id,))
    account_data = cursor.fetchall()
    for row in account_data:
        first_name = row[0]
        last_name = row[1]

    disconnect(conn)

    return first_name, last_name

# checks if there is a user and return user id if so
def is_account(username):
    account_sql = 'SELECT account_id FROM accounts WHERE account_username = ? AND account_is_active = 1;'

    conn, cursor = connect()

    cursor.execute(account_sql, (username,))
    account_data = cursor.fetchall()

    disconnect(conn)

    if account_data:
        for row in account_data:
            id = row[0]
        
        return id
    else: return 0

# gets user object
def get_account(account_id):
    account_sql = 'SELECT * FROM accounts WHERE account_id = ? AND account_is_active = 1;'

    conn, cursor = connect()

    cursor.execute(account_sql, (account_id,))
    account_data = cursor.fetchall()

    disconnect(conn)

    if account_data:
        return account_data[0]
    else: return 0

# returns the most recent transaction date recorded for a person's account. Takes in account id
def latest_transaction_date(account_id):
    sql = 'SELECT MAX(DISTINCT transaction_date) FROM transactions WHERE account_id = ? AND transaction_is_active = 1;'
    rows = select(sql=sql, items=[account_id])

    if rows:
        for row in rows:
            return row[0]
        
def get_transaction_category_id(account_id, name):
    sql = 'SELECT transaction_category_id FROM transaction_categories WHERE account_id = ? AND transaction_category_name = ? AND transaction_category_is_active = 1;'
    rows = select(sql=sql, items=[account_id, name])

    if rows:
        for row in rows:
            return row[0]
        
def get_budget_goal_id(account_id, name):
    sql = 'SELECT budget_goal_id FROM budget_goals WHERE account_id = ? AND budget_goal_name = ? AND budget_goal_is_active = 1;'
    rows = select(sql=sql, items=[account_id, name])

    if rows:
        for row in rows:
            return row[0]
        
def search_transactions(account_id, min_date, max_date, category, sort_by, asc, top=20):
    items = []
    date_str = ''
    category_str = ''
    sort_str = ''

    items.append(top)

    if min_date and max_date:
        date_str = 'WHERE t.transaction_date >= ? AND t.transaction_date <= ? AND t.transaction_is_active=1 '
        items.append(min_date)
        items.append(max_date)
    elif min_date:
        date_str = 'WHERE t.transaction_date >= ? AND t.transaction_is_active=1 '
        items.append(min_date)
    elif max_date:
        date_str = 'WHERE t.transaction_date <= ? AND t.transaction_is_active=1 '
        items.append(max_date)
    else:
        date_str = 'WHERE t.transaction_is_active=1 '

    if category == -1:
        category_str = ''
    else:
        category_str = 'AND t.transaction_category_id = ? '
        items.append(category)

    if sort_by == 'date':
        sort_str = 'ORDER BY t.transaction_date '
    elif sort_by == 'value':
        sort_str = 'ORDER BY t.transaction_value '

    if asc == True:
        sort_str = sort_str + 'asc;'
    else: 
        sort_str = sort_str + 'desc;'

    sql = 'SELECT TOP(?) t.transaction_id, t.transaction_date, t.transaction_value, t.transaction_category_id, tc.transaction_category_name FROM transactions t INNER JOIN transaction_categories tc ON t.transaction_category_id = tc.transaction_category_id '
    sql = sql + date_str + category_str + 'AND t.account_id = ? ' + sort_str

    items.append(account_id)

    rows = select(sql=sql, items=items)
    return rows

def fill_starter(account_id):
    bucket_sql = f"INSERT INTO budget_goals (account_id, budget_goal_target_value, budget_goal_name, budget_goal_desc) VALUES ({account_id}, 300, 'Dining Out', 'Eating out'), ({account_id}, 500, 'Groceries', 'Groceries'), ({account_id}, 300, 'Leisure', 'Leisure & entertainment'), ({account_id}, 400, 'Necessities', 'Living necessities'), ({account_id}, 200, 'Automobile', ?);"

    insert(bucket_sql, items=['Gas and Vehicle Maintenance'])

    dining = get_budget_goal_id(account_id=account_id, name="Dining Out")
    grocery = get_budget_goal_id(account_id=account_id, name="Groceries")
    leisure = get_budget_goal_id(account_id=account_id, name="Leisure")
    nec = get_budget_goal_id(account_id=account_id, name="Necessities")
    auto = get_budget_goal_id(account_id=account_id, name="Automobile")

    cat_sql = f"INSERT INTO transaction_categories (account_id, budget_goal_id, transaction_category_name, transaction_category_desc) VALUES ({account_id}, {dining}, 'Dining Out', 'Ate out'), ({account_id}, {grocery}, 'Groceries', 'Groceries'), ({account_id}, {leisure}, 'Leisure', 'Leisure & entertainment'), ({account_id}, {leisure}, 'Movies', 'Movie tickets and snacks'), ({account_id}, {nec}, 'Clothing', 'New clothes'), ({account_id}, {nec}, 'Necessity', 'Living necessities'), ({account_id}, {auto}, 'Gas', 'Gas for vehicle'), ({account_id}, {leisure}, 'Travel', 'Travel Expenses: Hotels & Transport'), ({account_id}, {leisure}, 'Transportation', 'Uber/Lyft, Public Transportation Fees'), ({account_id}, {auto}, 'Vehicle Maintenance', 'Vehicle Maintenance'), ({account_id}, {nec}, 'Home Goods', ?);"

    insert(cat_sql, items=['Living necessities and maintenance for the Home'])

def update_starter(account_id, income):
    default_auto = False

    if 0.1 * float(income) > 200.0:
        income = float(income) - 200.0
        default_auto = True

    buckets = {
        "auto" : 200.0 if default_auto else round(0.1 * float(income), 2),
        "dining" : round(0.25 * float(income), 2),
        "grocery" : round(0.3 * float(income), 2),
        "leisure" : round(0.3 * float(income), 2),
        "nec" : round(0.15 * float(income), 2)
    }

    dining = get_budget_goal_id(account_id=account_id, name="Dining Out")
    grocery = get_budget_goal_id(account_id=account_id, name="Groceries")
    leisure = get_budget_goal_id(account_id=account_id, name="Leisure")
    nec = get_budget_goal_id(account_id=account_id, name="Necessities")
    auto = get_budget_goal_id(account_id=account_id, name="Automobile")

    sql = "UPDATE budget_goals SET budget_goal_target_value = ? WHERE budget_goal_id = ?;"

    update(sql=sql, items=[buckets['dining'], dining])
    update(sql=sql, items=[buckets['auto'], auto])
    update(sql=sql, items=[buckets['grocery'], grocery])
    update(sql=sql, items=[buckets['leisure'], leisure])
    update(sql=sql, items=[buckets['nec'], nec])

def get_account_id(username):
    sql = "SELECT account_id FROM accounts WHERE account_username = ? AND account_is_active = 1;"

    rows = select(sql=sql, items=[username])

    if rows:
        for row in rows:
            return row[0]
    else:
        return -1

def check_new_user(account_id):
    sql = "SELECT LAST_LOGIN_DATE FROM accounts WHERE account_id = ? AND account_is_active = 1 AND LAST_LOGIN_DATE IS NULL;"

    rows = select(sql=sql, items=[account_id])

    if rows:
        return True
    else: return False
