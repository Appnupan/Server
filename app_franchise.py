# ������ ��û�� ������ ���Ʈ���� ��Ƶ� app_franchise.py
import uuid
import pymysql
from flask_cors import CORS
from flask import Blueprint, jsonify, request
from marshmallow import Schema, fields, validate, ValidationError

from dbconn import dbcon, dbclose


app_franchise = Blueprint('franchise', __name__)
CORS(app_franchise)


# ������� ��Ű�� ����
class PendingstoresSchema(Schema):
    tempstoreid = fields.Int(dump_only=True)  # tempstoreid�� �б� ����
    storename = fields.Str(required=True, validate=validate.Length(max=200))
    address = fields.Str(validate=validate.Length(max=200))
    contact = fields.Str(validate=validate.Length(max=50))
    memo = fields.Str()
    status = fields.Int()
    ownerid = fields.Str(required=True, validate=validate.Length(max=45))
    businessnumber = fields.Str(validate=validate.Length(max=45))
    businessdate = fields.Str(validate=validate.Length(max=45))
    bossname = fields.Str(validate=validate.Length(max=45))


# ���� ������ ��û�� ���� ��ü
franchise_schema = PendingstoresSchema()
# ������ ��ȸ�� ������ ������ ��û ����� �������� ���� ��ü
franchises_schema = PendingstoresSchema(many=True)


# ���ְ� ó�� ������ ��û�� �ϴ� ���Ʈ
@app_franchise.route('/regist', methods=['POST'])
def store_regist():
    data = request.get_json()
    
    try:
        validated_data = franchise_schema.load(data)
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400

    # �ʼ� �Է� ������
    storename = validated_data['storename']
    ownerid = validated_data['ownerid']
    
    # ���û���
    address = validated_data.get('address', None)
    contact = validated_data.get('contact', None)
    businessnumber = validated_data.get('businessnumber', None)
    businessdate = validated_data.get('businessdate', None)
    bossname = validated_data.get('bossname', None)

    conn = dbcon()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor() as cursor:
            # ������ ��û ������ pendingstores ���̺� ����
            sql = """
            INSERT INTO pendingstores (storename, address, contact, ownerid, memo, status, businessnumber, businessdate, bossname)
            VALUES (%s, %s, %s, %s, NULL, NULL, %s, %s, %s)
            """
            cursor.execute(sql, (storename, address, contact, ownerid, businessnumber, businessdate, bossname))
            conn.commit()

        return jsonify({"success": "Store added successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        dbclose(conn)


# ���� ���θ� ��ٸ��� ��� ���� ������ ȣ���ϴ� ���Ʈ
@app_franchise.route('', methods=['GET'])
def get_pendingstores():
    # DB ����
    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cursor:
            # status�� NULL�� pendingstores���� ������ ��ȸ
            sql = """
            SELECT tempstoreid, ownerid, storename, address, contact, businessnumber
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
                tempstoreid, ownerid, storename, address, contact, businessnumber = result
                pending_stores.append({
                    'tempstoreid': tempstoreid,
                    'ownerid': ownerid,
                    'storename': storename,
                    'address': address,
                    'contact': contact,
                    'businessnumber': businessnumber
                })

            return jsonify({'pendingStores': franchises_schema.dump(pending_stores)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        # DB ���� ����
        dbclose(conn)


# ������ ��û ���� ���Ʈ
@app_franchise.route('/confirm', methods=['POST'])
def store_confirm():
    # JSON �����ͷκ��� tempstoreid �޾ƿ���
    data = request.get_json()
    try:
        tempstore_id = data['tempstoreid']
    except KeyError:
        return jsonify({'error': 'tempstoreid is required'}), 400
    
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


# ������ ��û�ź��ϴ� ���Ʈ
@app_franchise.route('/deny', methods=['PUT'])
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

