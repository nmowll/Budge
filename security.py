import hashlib
import secrets
import pypyodbc as odbc
import pandas as pd
import db

def generate_salt():
    return secrets.token_bytes(16)

def verify_account(current_username, current_password):
    
    sql = 'SELECT account_password_hash, account_password_salt FROM accounts WHERE account_username = ? AND account_is_active = 1;'
    user = db.select(sql, [current_username])

    if user:
        user_data = user[0]

        hasher = hashlib.sha256()

        hasher.update(bytes.fromhex(user_data[1]) + current_password.encode())

        if hasher.hexdigest() == user_data[0]:

            sql3 = 'SELECT account_id FROM accounts WHERE account_username = ?;'
            row = db.select(sql3, [current_username])

            row_data = row[0]
            return row_data[0]
        else:
            return 0
    else:
        return 0
