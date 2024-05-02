# ���Ʈ ������ ���� app.py
from flask  import Flask, jsonify, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt

import pymysql
from dbconn import dbcon, dbclose
from regist_model import Registration

app = Flask(__name__)
CORS(app)
# Bcrypt �ν��Ͻ� �ʱ�ȭ
bcrypt = Bcrypt(app)

# user ȸ������ ���Ʈ
@app.route('/user/register', methods=['POST', 'GET'])
def user_register():
    # POST ��û�� ȸ������ ���� ó��
    if request.method == 'POST':
        userID = request.json.get('userid')  
        password = request.json.get('password')
        userName = request.json.get('username')
        userContact = request.json.get('usercontact')

        # ���ڰ��� ���� �Ǿ��� ���
        if not all([userID, userName, password, userContact]): 
            return jsonify({'error': 'Missing fields'}), 400
        
        response = Registration.register(bcrypt, userID, password, userName, userContact, 'users')
        return jsonify({'message': response}), 201
        
    elif request.method == 'GET':
        # GET ��û ��, userid �ߺ� üũ ����
        userID = request.args.get('userid')
        
        # ���� ���� �����Ǿ��ٸ�
        if not userid:
            return jsonify({'error': 'userid is required for duplication check'}), 400

        conn = dbcon()
        cur = conn.cursor()
        # �����ͺ��̽����� userid Ȯ��
        cur.execute("SELECT userid FROM users WHERE userid = %s", (userID,))
        user_exists = cur.fetchone()
        dbclose(conn)

        if user_exists:
            return jsonify({'message': 'This userid is already taken'}), 409
        else:
            return jsonify({'message': 'This userid is available'}), 200
            

# user �α��� ���Ʈ
@app.route('/user/login', methods=['POST'])
def user_login():
    # Ŭ���̾�Ʈ�κ��� userid�� password �ޱ�
    userid = request.json.get('userid')
    password = request.json.get('password')

    # �Է°� ����
    if not userid or not password:
        return jsonify({'error': 'Missing fields'}), 400

    conn = dbcon()
    cur = conn.cursor()
    
    try:
        # �ش� userid�� �´� userigest �ҷ�����
        cur.execute("SELECT userdigest FROM users WHERE userid = %s", (userid,))
        user = cur.fetchone()
        # �̹� �ִ� ����ڶ��
        if user:
            userdigest = user[0]
            
            # ��й�ȣ ����
            if bcrypt.check_password_hash(userdigest, password):
                return jsonify({'message': 'Login success!'}), 200
                
            else:
                return jsonify({'error': 'Please check your password'}), 401
        # ���� ����  ����ڶ��
        else:
            return jsonify({'error': 'Join APP-nupan first'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        dbclose(conn)


# ���� ȸ������ ���Ʈ
@app.route('/owner/register', methods=['POST'])
def owner_register():
    ownerID = request.json.get('ownerid')
    password = request.json.get('password')
    ownerName = request.json.get('ownername')
    ownerContact = request.json.get('ownercontact')
    
    # ���ڰ��� ���� �Ǿ��� ���
    if not all([ownerID, password, ownerName, ownerContact]): 
        return jsonify({'error': 'Missing fields'}), 400
    
    response = Registration.register(bcrypt, ownerID, password, ownerName, ownerContact, 'owners')
    return jsonify({'message': response}), 201


@app.route('/owner/login', methods=['POST'])
def owner_login():
    ownerid = request.json.get('ownerid')
    password = request.json.get('password')

    # �Է°� ����
    if not ownerid or not password:
        return jsonify({'error': 'Missing fields'}), 400

    conn = dbcon()
    cur = conn.cursor()
    
    try:
        # Owners ���̺��� �ش� ownerid �˻�
        cur.execute("SELECT ownerdigest FROM owners WHERE ownerid = %s", (ownerid,))
        owner = cur.fetchone()

        if owner:
            ownerdigest = owner[0]
            
            if bcrypt.check_password_hash(ownerdigest, password):
                return jsonify({'message': 'Login success!'}), 200
                
            else:
                return jsonify({'error': 'Please check your password'}), 401
                
        else:
            return jsonify({'error': 'Please join APP-nupan first'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        dbclose(conn)


@app.route('/store/11111/menu', methods=['GET'])
def get_menu():
    # �����ͺ��̽� ����
    conn = dbcon()  # ������ �Լ� ȣ��
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Ŀ�� ����
        cursor = conn.cursor(pymysql.cursors.DictCursor)  # ����� ��ųʸ� ���·� �ޱ� ���� ����

        # SQL ���� ����
        query = "SELECT * FROM storemenu"
        cursor.execute(query)

        # ��� �����͸� ������ ����
        rows = cursor.fetchall()

        # Ŀ���� �����ͺ��̽� ���� ����
        cursor.close()
        dbclose(conn)  # ������ �Լ� ȣ��

        # ����� JSON ���·� Ŭ���̾�Ʈ�� ������
        return jsonify(rows)

    except pymysql.MySQLError as e:
        print(f"Query failed: {e}")
        return jsonify({"error": "Query failed"}), 500
        
        
@app.route('/store/11111', methods=['GET'])
def get_stores():
    # �����ͺ��̽� ����
    conn = dbcon()  # ������ �Լ� ȣ��
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # Ŀ�� ����
        cursor = conn.cursor(pymysql.cursors.DictCursor)  # ����� ��ųʸ� ���·� �ޱ� ���� ����

        # SQL ���� ����
        query = "SELECT * FROM stores"
        cursor.execute(query)

        # ��� �����͸� ������ ����
        rows = cursor.fetchall()

        # Ŀ���� �����ͺ��̽� ���� ����
        cursor.close()
        dbclose(conn)  # ������ �Լ� ȣ��

        # ����� JSON ���·� Ŭ���̾�Ʈ�� ������
        return jsonify(rows)

    except pymysql.MySQLError as e:
        print(f"Query failed: {e}")
        return jsonify({"error": "Query failed"}), 500