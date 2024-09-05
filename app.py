'''
# ���Ʈ ������ ���� app.py
from flask  import Flask, jsonify, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

import os
import uuid
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
        if not userID:
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


# ���� �α��� ���Ʈ
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
            
            # ��й�ȣ ����
            if bcrypt.check_password_hash(ownerdigest, password):
                # Stores ���̺��� ownerid�� �ش��ϴ� storeid �˻�
                cur.execute("SELECT storeid, storename FROM stores WHERE ownerid = %s", (ownerid,))
                store = cur.fetchone()

                if store:
                    storeid = store[0]
                    storename = store[1]
                    return jsonify({'message': 'Login success!', 'storeid': storeid, 'storename': storename}), 200
                else:
                    # �ش� ownerid�� ��ϵ� ���԰� ���� ���
                    return jsonify({'error': 'No store found for this owner'}), 404

            else:
                return jsonify({'error': 'Please check your password'}), 401
                
        else:
            return jsonify({'error': 'Please join APP-nupan first'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        dbclose(conn)


# ������ ��û ���Ʈ
@app.route('/store/regist', methods=['POST'])
def store_regist():
    # JSON �����Ϳ��� storename, address, contact ���� ����
    data = request.get_json()
    storename = data.get('storename')
    address = data.get('address')
    contact = data.get('contact')
    ownerid = data.get('ownerid')
    
    # �����ͺ��̽� ����
    conn = dbcon()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        with conn.cursor() as cursor:
            # SQL ���� ����
            sql = """
            INSERT INTO pendingstores (storename, address, contact, ownerid, memo, status)
            VALUES (%s, %s, %s, %s, NULL, NULL)
            """
            cursor.execute(sql, (storename, address, contact, ownerid))
            conn.commit()
        
        return jsonify({"success": "Store added successfully"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        # �����ͺ��̽� ���� ����
        dbclose(conn)


@app.route('/store', methods=['GET'])
def get_pendingstores():
    # DB ����
    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cursor:
            # status�� NULL�� pendingstores���� ������ ��ȸ
            sql = """
            SELECT tempstoreid, ownerid, storename, address, contact
            FROM pendingstores
            WHERE status IS NULL
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            
            # ����� ���� ���
            if not results:
                return jsonify({'error': 'No pending stores found'}), 404
            
            # ����� JSON �������� ��ȯ
            pending_stores = []
            for result in results:
                tempstoreid, ownerid, storename, address, contact = result
                pending_stores.append({
                    'tempstoreid': tempstoreid,
                    'ownerid': ownerid,
                    'storename': storename,
                    'address': address,
                    'contact': contact
                })

            return jsonify({'pendingStores': pending_stores}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # DB ���� ����
        dbclose(conn)


@app.route('/store/confirm', methods=['POST'])
def store_confirm():
    # JSON �����ͷκ��� tempstoreid �޾ƿ���
    data = request.get_json()
    tempstore_id = data['tempstoreid']
    
    # DB ����
    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cursor:
            # pendingstores���� ���ε��� ���� ������ ��ȸ
            sql = """
            SELECT ownerid, storename, address, contact
            FROM pendingstores
            WHERE tempstoreid = %s AND status IS NULL
            """
            cursor.execute(sql, (tempstore_id,))
            result = cursor.fetchone()
            if result:
                ownerid, storename, address, contact = result

                # storeid�� ����� ���� UID ����
                storeid = str(uuid.uuid4())

                # stores ���̺� ������ ����
                insert_sql = """
                INSERT INTO stores (storeid, ownerid, storename, address, storecontact)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(insert_sql, (storeid, ownerid, storename, address, contact))
                
                # pendingstores ���̺��� status ������Ʈ
                update_sql = """
                UPDATE pendingstores
                SET status = 1
                WHERE tempstoreid = %s
                """
                cursor.execute(update_sql, (tempstore_id,))
                
                conn.commit()

                return jsonify({'success': 'Store confirmed', 'storeid': storeid}), 200
            else:
                return jsonify({'error': 'No data found with provided tempstoreid or already processed'}), 404
    
    except pymysql.MySQLError as e:
        print(f"SQL Error: {e}")
        return jsonify({'error': str(e)}), 500
    
    finally:
        # DB ���� ����
        dbclose(conn)


@app.route('/store/deny', methods=['PUT'])
def store_deny():
    # JSON �����ͷκ��� tempstoreid �޾ƿ���
    data = request.get_json()
    tempstore_id = data['tempstoreid']
    
    # DB ����
    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cursor:
            # pendingstores ���̺��� status�� 0���� ������Ʈ
            update_sql = """
            UPDATE pendingstores
            SET status = 0
            WHERE tempstoreid = %s AND status IS NULL
            """
            affected_rows = cursor.execute(update_sql, (tempstore_id,))
            conn.commit()

            if affected_rows == 0:
                # �ش� ID�� �̹� ó���Ǿ��ų� �������� �ʴ� ���
                return jsonify({'error': 'No pending store found with provided tempstoreid or already processed'}), 404
            return jsonify({'success': 'Store application has been denied'}), 200
    except pymysql.MySQLError as e:
        print(f"SQL Error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        # DB ���� ����
        dbclose(conn)


# ���� �޴� ����ϴ� ���Ʈ
# ��Ƽ��Ʈ/������ ������
@app.route('/store/<string:ownerid>/menu', methods=['POST'])
def storemenu_post(ownerid):
    # form-data�κ��� ���� ��������
    productname = request.form.get('productname')
    storename = request.form.get('storename')
    price = request.form.get('price')
    category = request.form.get('category')
    menuimage = request.files.get('menuimage')

    if not menuimage:
        return jsonify({'error': 'No image provided'}), 400

    # �̹��� ������ �����ϰ� �����ϱ� ���� ���ϸ� ����
    filename = secure_filename(menuimage.filename)
    
    # �ӽ� ���� ��� ����
    temp_path = os.path.join('/home/ubuntu/appnupan/tmp', filename)
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    menuimage.save(temp_path)

    # ������ ���� BLOB���� �����ͺ��̽��� ����
    with open(temp_path, 'rb') as file:
        binary_data = file.read()

    # DB ����
    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cursor:
            # storemenu ���̺� ������ ����
            sql = """
            INSERT INTO storemenu (storeid, productname, storename, price, menuimage, category)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (ownerid, productname, storename, price, binary_data, category))
            conn.commit()

            return jsonify({'success': 'Menu item added successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # �ӽ� ���� ����
        os.remove(temp_path)
        # DB ���� ����
        dbclose(conn)


'''