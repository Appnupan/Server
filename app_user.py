# �� ������� ȸ������, �α���, ID �ߺ�üũ ���Ʈ���� ��Ƶ� ��� ���� app_user.py
import pymysql
from flask_cors import CORS
from flask import Blueprint, jsonify, request
from flask_bcrypt import Bcrypt
from marshmallow import Schema, fields, validate, ValidationError

from dbconn import dbcon, dbclose
from model_regist import Registration


app_user = Blueprint('app_user', __name__)
CORS(app_user)
# bcrypt �ν��Ͻ� ����, ������ ���߿� �۰� ���ε�
bcrypt = Bcrypt()


# Bcrypt �ν��Ͻ� �ʱ�ȭ �Լ�
def init_bcrypt(app):
    global bcrypt
    bcrypt = Bcrypt(app)


# JSON ������ ����ȭ
class UserSchema(Schema):
    userid = fields.String(required=True, validate=[validate.Length(min=1, max=45)])
    username = fields.String(required=True, validate=[validate.Length(min=1, max=45)])
    password = fields.String(required=True, validate=[validate.Length(min=1)])
    usercontact = fields.String(validate=[validate.Length(max=45)])

# ���� ������� �ֹ��̷� Ȯ�� ��Ű��
class UserHistorySchema(Schema):
    userid = fields.String(required=True, validate=[validate.Length(min=1, max=45)])

# ���� ȣ�� ��Ű��
class CallStaffSchema(Schema):
    orderid = fields.String(required=True)


# ȸ�������� ���� ������� ��Ű�� ��ü ����
user_schema = UserSchema()
# ���� ������� �ֹ��̷� Ȯ�� ��Ű�� ��ü ����
user_history_schema = UserHistorySchema()
# ���� ȣ�� ��Ű�� ��ü
call_staff_schema = CallStaffSchema()



# ȸ������ ���Ʈ �����δ� baseURL/user/regist
@app_user.route('/register', methods=['POST'])
def register_user():
    try:
        user_data = user_schema.load(request.json)
        userid = user_data['userid']

        # �����ͺ��̽����� �ߺ��� ID Ȯ��
        conn = dbcon()
        cur = conn.cursor()
        cur.execute("SELECT userid FROM users WHERE userid = %s", (userid,))
        if cur.fetchone():
            return jsonify({'message': 'This userid is already taken'}), 409

        registration = Registration(bcrypt)  # ���⼭ Registration �ν��Ͻ� ���� �ٵ� bcrypt�� �����
        response = registration.register_user(user_data['userid'], user_data['password'], user_data['username'], user_data['usercontact'])
        return jsonify({'message': response}), 201
        
    except ValidationError as err:
        return jsonify(err.messages), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        dbclose(conn)


# ID �ߺ��˻� ���Ʈ �����δ� baseURL/user/check?userid=������ Ŭ���̾�Ʈ�� ��û�ϴ� �����id
# userid�� Ŭ���̾�Ʈ���� ������ ������ ���� ����� id
@app_user.route('/check', methods=['GET'])
def check_userid():
    userid = request.args.get('userid')

    if not userid:
        return jsonify({'error': 'userid parameter is required'}), 400
    
    try:
        conn = dbcon()
        cur = conn.cursor()
        cur.execute("SELECT userid FROM users WHERE userid = %s", (userid,))

        if cur.fetchone():
            return jsonify({'isAvailable': False, 'message': 'This userid is already taken'}), 200
        else:
            return jsonify({'isAvailable': True, 'message': 'This userid is available'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        dbclose(conn)


# �α��� ���Ʈ �����δ� baseURL/user/login
@app_user.route('/login', methods=['POST'])
def login_user():
    userid = request.json.get('userid')
    password = request.json.get('password')
    conn = dbcon()
    cur = conn.cursor()

    try:
        # userdigest�� �˻��ϴ� ��� username�� �Բ� �˻�
        cur.execute("SELECT userdigest, username FROM users WHERE userid = %s", (userid,))
        row = cur.fetchone()

        if row:
            # �����ͺ��̽� ��ȸ ������� userdigest�� username ����
            userdigest, username = row

            # ��й�ȣ ����
            if bcrypt.check_password_hash(userdigest, password):
                return jsonify({'message': 'Login success!', 'username': username}), 200

        return jsonify({'error': 'Invalid credentials'}), 401
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        dbclose(conn)


# ���� ȣ�� ���Ʈ
@app_user.route('/call', methods=['POST'])
def call_staff():
    json_data = request.get_json()
    
    try:
        data = call_staff_schema.load(json_data)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    orderid = data['orderid']
    
    conn = dbcon()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor() as cursor:
            # orders ���̺��� staffcall ���� 1�� ������Ʈ
            query_update_staffcall = """
                UPDATE orders SET staffcall = 1 WHERE orderid = %s
            """
            cursor.execute(query_update_staffcall, (orderid,))
            
            # ������� Ŀ��
            conn.commit()
            
            return jsonify({"message": "Staff call updated successfully"}), 200

    except pymysql.MySQLError as e:
        # ���� �߻� �� �ѹ�
        conn.rollback()
        return jsonify({"error": "Query failed", "details": str(e)}), 500

    finally:
        dbclose(conn)


# ���� ������� �ֹ����� ��ȸ ���Ʈ
@app_user.route('/history', methods=['POST'])
def user_order_history():
    json_data = request.get_json()
    try:
        data = user_history_schema.load(json_data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    userid = data.get('userid')

    conn = dbcon()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            query_get_orders = "SELECT orderid, ordertime FROM orders WHERE userid = %s"
            cursor.execute(query_get_orders, (userid,))
            orders = cursor.fetchall()

            if not orders:
                return jsonify({"message": "No orders found for this user"}), 404

            order_history = []

            for order in orders:
                orderid = order['orderid']
                ordertime = order['ordertime']
                
                # order_details ���̺��� orderid�� �޴� ���� ��ȸ
                query_get_order_details = """
                    SELECT menu_name, quantity, total_price
                    FROM order_details
                    WHERE orderid = %s
                """
                cursor.execute(query_get_order_details, (orderid,))
                order_details = cursor.fetchall()

                # orders ���̺��� ownerid ��ȸ
                query_get_owner = "SELECT ownerid FROM orders WHERE orderid = %s"
                cursor.execute(query_get_owner, (orderid,))
                owner = cursor.fetchone()

                if owner:
                    ownerid = owner['ownerid']
                    
                    # stores ���̺��� storename ��ȸ
                    query_get_store_name = "SELECT storename FROM stores WHERE ownerid = %s"
                    cursor.execute(query_get_store_name, (ownerid,))
                    store = cursor.fetchone()
                    storename = store['storename'] if store else "Unknown Store"
                else:
                    storename = "Unknown Store"

                order_info = {
                    "orderid": orderid,
                    "total_price": order_details[0]['total_price'] if order_details else 0,
                    "ordertime": ordertime,
                    "storename": storename,
                    "items": [{"menu_name": detail["menu_name"], "quantity": detail["quantity"]} for detail in order_details]
                }

                order_history.append(order_info)

            return jsonify(order_history), 200

    except pymysql.MySQLError as e:
        return jsonify({"error": "Query failed", "details": str(e)}), 500

    finally:
        dbclose(conn)


# ��й�ȣ ���� ���Ʈ
@app_user.route('/<string:userid>/changepw', methods=['PUT'])
def change_user_pw(userid):
    try:
        # ��û���� ��й�ȣ�� ����
        new_password = request.json.get('password')
        # ��й�ȣ �ؽ�
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')

        conn = dbcon()
        cur = conn.cursor()

        # ��й�ȣ ������Ʈ
        sql = "UPDATE users SET userdigest = %s WHERE userid = %s"
        cur.execute(sql, (hashed_password, userid))
        conn.commit()
        
        return jsonify({'message': 'Password updated successfully'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        dbclose(conn)
