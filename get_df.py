import pandas as pd
import db
import security

account_id = security.verify_account(current_username='nmowll',current_password='FatLodi@SlimBenny2001$')

def generate_budget_goals_df(account_id, year=2024, month=6):
    # defining the sql queries for getting the data
    transaction_sql = "SELECT t.transaction_value, t.transaction_date, bg.budget_goal_target_value, bg.budget_goal_name FROM transactions t INNER JOIN transaction_categories tc ON t.transaction_category_id = tc.transaction_category_id INNER JOIN budget_goals bg ON tc.budget_goal_id = bg.budget_goal_id WHERE t.account_id = ? AND t.transaction_date >= '"+str(month)+'/1/'+str(year)+"' AND t.transaction_date < '"+str(month + 1 if month < 12 else 1)+'/1/'+str(year if month < 12 else year + 1)+"' AND t.transaction_is_active = 1;"
    budget_goals_sql = 'SELECT budget_goal_target_value AS goal_target_amount, budget_goal_name AS goal_name FROM budget_goals WHERE account_id = ? AND budget_goal_is_active = 1;'

    # connect to db and execute queries, extracting information
    conn, cursor = db.connect()

    cursor.execute(transaction_sql, (account_id,))
    transaction_data = cursor.fetchall()
    transaction_columns = [col[0] for col in cursor.description]

    cursor.execute(budget_goals_sql, (account_id,))
    active_goals_data = cursor.fetchall()

    db.disconnect(conn)

    # creating active goals dictionary with target amounts
    goals_dict = {}
    for row in active_goals_data:
        goals_dict[row[1]] = row[0]

    # creating pandas df
    transactions = pd.DataFrame(transaction_data, columns=transaction_columns)

    transactions['transaction_date'] = pd.to_datetime(transactions['transaction_date'], format='%Y-%m-%d')

    # extracting needed date information
    transactions['year'] = pd.DatetimeIndex(transactions['transaction_date']).year
    transactions['month'] = pd.DatetimeIndex(transactions['transaction_date']).month
    transactions.drop(columns=['transaction_date'], inplace=True)

    transactions.rename(columns={'transaction_value':'transaction_amount','budget_goal_target_value':'goal_target_amount','budget_goal_name':'goal_name'}, inplace=True)

    budget_goals_df = transactions.groupby(['year','month','goal_name','goal_target_amount'], as_index=False)['transaction_amount'].sum()

    budget_goals_df['plot_overdraft'] = 0
    budget_goals_df['plot_overdraft'].mask(budget_goals_df['transaction_amount'] > budget_goals_df['goal_target_amount'], other=(budget_goals_df['transaction_amount'] - budget_goals_df['goal_target_amount']), inplace=True)

    budget_goals_df['plot_budget_remaining'] = 0
    budget_goals_df['plot_budget_remaining'].mask(budget_goals_df['transaction_amount'] < budget_goals_df['goal_target_amount'], other=(budget_goals_df['goal_target_amount'] - budget_goals_df['transaction_amount']), inplace = True)

    budget_goals_df['plot_amount_spent'] = budget_goals_df['transaction_amount']
    budget_goals_df['plot_amount_spent'].mask(budget_goals_df['transaction_amount'] > budget_goals_df['goal_target_amount'], other=(budget_goals_df['goal_target_amount']), inplace=True)

    goal_fillers = []
    current_goals = budget_goals_df['goal_name'].unique()
    for goal in goals_dict.keys():
        if goal not in current_goals:
            goal_fillers.append([year, month, goal, goals_dict[goal], 0, 0, goals_dict[goal], 0])

    column_names = ['year','month','goal_name','goal_target_amount','transaction_amount','plot_overdraft','plot_budget_remaining','plot_amount_spent']

    if goal_fillers:
        goal_fillers_df = pd.DataFrame(goal_fillers)
        goal_fillers_df.columns = column_names
        budget_goals_df = pd.concat([budget_goals_df, goal_fillers_df])
    
    budget_goals_df.sort_values(by='goal_target_amount', ascending=False, inplace=True)
    budget_goals_df.reset_index(drop=True, inplace=True)

    return budget_goals_df


def generate_weekly_df(account_id, year=2024, month=6):
    # defining the sql queries for getting the data
    transaction_sql = "SELECT t.transaction_value, t.transaction_date, bg.budget_goal_target_value, bg.budget_goal_name FROM transactions t INNER JOIN transaction_categories tc ON t.transaction_category_id = tc.transaction_category_id INNER JOIN budget_goals bg ON tc.budget_goal_id = bg.budget_goal_id WHERE t.account_id = ? AND t.transaction_date >= '"+str(month)+'/1/'+str(year)+"' AND t.transaction_date < '"+str(month + 1 if month < 12 else 1)+'/1/'+str(year if month < 12 else year + 1)+"' AND t.transaction_is_active = 1;"

    # connect to db and execute queries, extracting information
    conn, cursor = db.connect()

    cursor.execute(transaction_sql, (account_id,))
    transaction_data = cursor.fetchall()
    transaction_columns = [col[0] for col in cursor.description]

    db.disconnect(conn)

    # creating pandas df
    transactions = pd.DataFrame(transaction_data, columns=transaction_columns)

    transactions['transaction_date'] = pd.to_datetime(transactions['transaction_date'], format='%Y-%m-%d')

    # extracting needed date information
    transactions['year'] = pd.DatetimeIndex(transactions['transaction_date']).year
    transactions['month'] = pd.DatetimeIndex(transactions['transaction_date']).month
    transactions['week'] = transactions['transaction_date'].dt.isocalendar().week

    transactions.drop(columns=['transaction_date'], inplace=True)

    transactions.rename(columns={'transaction_value':'transaction_amount','budget_goal_target_value':'goal_target_amount','budget_goal_name':'goal_name'}, inplace=True)

    weekly_df = transactions.groupby(['year','month','week','goal_name'], as_index=False)['transaction_amount'].sum()
    weekly_df.sort_values(by='goal_name', ascending=True, inplace=True)

    weekly_df.reset_index(drop=True, inplace=True)

    return weekly_df


def get_years_months_list(account_id):
    sql = 'SELECT DISTINCT transaction_date FROM transactions WHERE account_id = ? AND transaction_is_active = 1;'
    rows = db.select(sql, [account_id])

    months = []
    years = []

    if rows:
        colum_name = ['date']
        df = pd.DataFrame(rows)
        df.columns = colum_name

        df['year'] = pd.DatetimeIndex(df['date']).year
        df['month'] = pd.DatetimeIndex(df['date']).month

        months = df['month'].unique()
        years = df['year'].unique()

    return years, months




