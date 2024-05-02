# DB���� ��� dbconn.py
import pymysql

def dbcon():
    try:
        conn = pymysql.connect(host='appnupan.c7ogkao424wk.ap-northeast-2.rds.amazonaws.com',
                               user='admin',
                               password='1q2w3e4r',
                               db='appnupan',
                               charset='utf8mb4')
                               
        # mysql ���� ����
        if conn.open: # DB ���� ���� Ȯ��
            print('Database connection successful')
        return conn

    except pymysql.MySQLError as e:
        print(f"Database connection failed: {e}")
        return None

def dbclose(conn):
    try:
        if conn:
            conn.close() # DB ���� ����
            print('Database connection closed')
            
    except pymysql.MySQLError as e:
        print(f"Error closing connection: {e}")