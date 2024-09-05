# ������ �޴��� qr����� ���� �� ��ȸ�ϴ� ���Ʈ���� ��Ƶ� ��� ���� app_store.py
import os
import pymysql
import qrcode
import logging

from flask_cors import CORS
from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
from marshmallow import Schema, fields, validate

from dbconn import dbcon, dbclose


app_store = Blueprint('store', __name__)
CORS(app_store)


# �α� ����
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# �̹��� ���� ��� Ȯ���ڿ� ũ�� ����
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB


# ������� ��Ű�� ����
class StoremenuSchema(Schema):
    productid = fields.Int(dump_only=True)
    productname = fields.Str(validate=validate.Length(max=100))
    storeid = fields.Str(validate=validate.Length(max=100))
    storename = fields.Str(validate=validate.Length(max=100))
    price = fields.Str(validate=validate.Length(max=20))
    available = fields.Int()
    menuimage = fields.Str(dump_only=True)  # �б� ���� �ʵ�� ����
    imageurl = fields.Str()  # �̹��� URL�� ����
    category = fields.Str(validate=validate.Length(max=50))
    description = fields.Str(validate=validate.Length(max=200))


# ���Ը޴��� �����ϱ� ���� ��Ű�� ��ü
storemenu_schema = StoremenuSchema()
# ������ ���� �޴��� ��ȯ�ϱ� ���� ��Ű�� ��ü
storemenus_schema = StoremenuSchema(many=True)


# ���� Ȯ���� Ȯ�� �Լ�
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


ELASTIC_IP = "43.201.92.62"


# ���Ը޴� ��� ���Ʈ
@app_store.route('/<string:ownerid>/menu', methods=['POST'])
def storemenu_post(ownerid):
    productname = request.values.get('productname')
    storename = request.values.get('storename')
    price = request.values.get('price')
    category = request.values.get('category')
    description = request.values.get('description')
    menuimage = request.files.get('menuimage')

    if not menuimage:
        return jsonify({'error': 'No image provided'}), 400

    if not allowed_file(menuimage.filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    # ���ݿ��� �޸��� �����Ͽ� ����
    price = price.replace(',', '')

    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cursor:
            sql_insert = """
            INSERT INTO storemenu (storeid, productname, storename, price, category, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_insert, (ownerid, productname, storename, price, category, description))
            conn.commit()

            cursor.execute("SELECT LAST_INSERT_ID() AS productid")
            result = cursor.fetchone()
            productid = result[0]  # Ʃ�ÿ��� ù ��° ��ҷ� ����

            file_extension = menuimage.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"{ownerid}_{productid}.{file_extension}")
            save_path = os.path.join('/home/ubuntu/appnupan/tmp', filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            menuimage.save(save_path)

            image_url = f"http://{ELASTIC_IP}/images/{filename}"

            sql_update = """
            UPDATE storemenu SET imageurl = %s WHERE productid = %s
            """
            cursor.execute(sql_update, (image_url, productid))
            conn.commit()

            sql_store_category = """
            INSERT INTO store_category (storeid, category)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE category = VALUES(category)
            """
            cursor.execute(sql_store_category, (ownerid, category))
            conn.commit()

            return jsonify({'success': 'Menu item added successfully', 'productid': productid}), 201

    except Exception as e:
        logger.error(f"Error adding menu item: {str(e)}")
        return jsonify({'error': 'Failed to add menu item', 'details': str(e)}), 500
    finally:
        dbclose(conn)


# �ش� ������ �޴����� ��ȯ�ϴ� ���Ʈ
@app_store.route('/<string:ownerid>/menu', methods=['GET'])
def storemenu_get(ownerid):
    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            SELECT productid, productname, storeid, storename, price, available, imageurl, category, description
            FROM storemenu
            WHERE storeid = %s
            """
            cursor.execute(sql, (ownerid,))
            results = cursor.fetchall()

            if not results:
                return jsonify({'error': 'No menu items found for the given storeid'}), 404

            return jsonify({'menu': results}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        dbclose(conn)


# ���� �޴� ���� ���Ʈ
@app_store.route('/<string:productid>/menu', methods=['PUT'])
def storemenu_update(productid):
    logger.info("Received request to update menu item with product ID: %s", productid)
    productname = request.values.get('productname')
    storename = request.values.get('storename')
    price = request.values.get('price')
    available = request.values.get('available')
    category = request.values.get('category')
    description = request.values.get('description')
    new_menuimage = request.files.get('menuimage')

    conn = dbcon()
    if conn is None:
        logger.error("Database connection failed")
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT storeid, imageurl FROM storemenu WHERE productid = %s", (productid,))
            menu_item = cursor.fetchone()
            if not menu_item:
                logger.error("Menu item not found with product ID: %s", productid)
                return jsonify({'error': 'Menu item not found'}), 404

            old_imageurl = menu_item['imageurl']
            storeid = menu_item['storeid']

            fields_to_update = []
            values_to_update = []

            if new_menuimage and allowed_file(new_menuimage.filename):
                if old_imageurl:
                    old_image_path = os.path.join('/home/ubuntu/appnupan/tmp', os.path.basename(old_imageurl))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                file_extension = new_menuimage.filename.rsplit('.', 1)[1].lower()
                new_filename = secure_filename(f"{storeid}_{productid}.{file_extension}")
                save_path = os.path.join('/home/ubuntu/appnupan/tmp', new_filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                new_menuimage.save(save_path)
                new_image_url = f"http://{ELASTIC_IP}/images/{new_filename}"
                fields_to_update.append("imageurl = %s")
                values_to_update.append(new_image_url)

            # ���ݿ��� �޸��� �����Ͽ� ����
            if price:
                price = price.replace(',', '')

            for field, value in [('productname', productname), ('storename', storename), 
                                 ('price', price), ('available', 1 if available else 0), 
                                 ('category', category), ('description', description)]:
                if value is not None:
                    fields_to_update.append(f"{field} = %s")
                    values_to_update.append(value)

            if not fields_to_update:
                logger.error("No valid fields provided for update")
                return jsonify({'error': 'No valid fields provided for update'}), 400

            query = f"UPDATE storemenu SET {', '.join(fields_to_update)} WHERE productid = %s"
            values_to_update.append(productid)

            cursor.execute(query, tuple(values_to_update))
            conn.commit()
            logger.info("Menu item updated successfully for product ID: %s", productid)
            return jsonify({'success': 'Menu item updated successfully'}), 200

    except Exception as e:
        logger.error("Error updating menu item: %s", str(e))
        return jsonify({'error': str(e)}), 500

    finally:
        dbclose(conn)


# �޴� ���� ���Ʈ
@app_store.route('/<string:productid>', methods=['DELETE'])
def storemenu_delete(productid):
    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # ���� �޴� ������ ��������
            cursor.execute("SELECT imageurl FROM storemenu WHERE productid = %s", (productid,))
            menu_item = cursor.fetchone()
            if not menu_item:
                return jsonify({'error': 'Menu item not found'}), 404

            image_url = menu_item['imageurl']

            # �޴� ����
            cursor.execute("DELETE FROM storemenu WHERE productid = %s", (productid,))
            conn.commit()

            # �̹��� ���� ����
            if image_url:
                image_path = os.path.join('/home/ubuntu/appnupan/tmp', os.path.basename(image_url))
                if os.path.exists(image_path):
                    os.remove(image_path)

            return jsonify({'success': 'Menu item deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        dbclose(conn)


# ������ ī�װ��� ��ȯ�ϴ� ���Ʈ
@app_store.route('/<string:ownerid>/category', methods=['GET'])
def get_categories(ownerid):
    try:
        conn = dbcon()
        cursor = conn.cursor()
        query = "SELECT category FROM store_category WHERE storeid = %s"
        cursor.execute(query, (ownerid,))
        categories = cursor.fetchall()
        dbclose(conn)
        
        if categories:
            return jsonify([category[0] for category in categories]), 200
        else:
            return jsonify({"message": "No categories found for this owner"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# qr_code�� ���� storetable ���̺��� ����ȭ
class StoretableSchema(Schema):
    tableid = fields.Int(dump_only=True)
    storeid = fields.Str(validate=validate.Length(max=100))
    tablenumber = fields.Int(validate=validate.Range(min=1))
    qr_path = fields.Str(validate=validate.Length(max=255))
    qr_code = fields.Str(validate=validate.Length(max=255))


# �����¼����� QR�ڵ� ������ ���� ��Ű�� ��ü ����
storetable_schema = StoretableSchema()
storetables_schema = StoretableSchema(many=True)


def generate_qr_code(ownerid, tablenumber):
    qr_data = f"http://{ELASTIC_IP}/qr/_{ownerid}_{tablenumber}.png"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    directory = '/home/ubuntu/appnupan/QR'
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    filename = f'_{ownerid}_{tablenumber}.png'
    file_path = os.path.join(directory, filename)
    img.save(file_path)
    
    return file_path, qr_data  # ���� ��ο� QR �����͸� ��ȯ


# �¼����� qr�ڵ� ����
@app_store.route('/<string:ownerid>/qr', methods=['POST'])
def qr_post(ownerid):
    data = request.json
    table_count = data.get('table_count')

    if not table_count or not isinstance(table_count, int):
        return jsonify({'error': 'Table count must be an integer'}), 400

    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT MAX(tablenumber) FROM storetable WHERE storeid = %s FOR UPDATE", (ownerid,))
            last_table_number = cursor.fetchone()[0] or 0

            sql = """
            INSERT INTO storetable (storeid, tablenumber, qr_path, qr_code)
            VALUES (%s, %s, %s, %s)
            """
            successful_inserts = 0
            qr_urls = []
            for i in range(1, table_count + 1):
                table_number = last_table_number + i
                qr_code_path, qr_data = generate_qr_code(ownerid, table_number)  # ���⼭ Ʃ���� ����
                qr_url = f'http://{ELASTIC_IP}/qr/{os.path.basename(qr_code_path)}'
                qr_urls.append(qr_url)

                # URL�� QR �����͸� DB�� ����
                cursor.execute(sql, (ownerid, table_number, qr_url, qr_data))
                successful_inserts += 1

            conn.commit()
            return jsonify({'success': 'QR codes saved successfully', 'count': successful_inserts, 'qr_urls': qr_urls}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        dbclose(conn)


# �ش� ������ QR�ڵ���� ��ȸ�ϴ� ���Ʈ
@app_store.route('/<string:ownerid>/qr', methods=['GET'])
def qr_get(ownerid):
    conn = dbcon()
    if conn is None:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("SELECT tablenumber, qr_path FROM storetable WHERE storeid = %s", (ownerid,))
            qr_codes = cursor.fetchall()

            if not qr_codes:
                return jsonify({'error': 'No QR codes found for the given ownerid'}), 404

            return jsonify({'qr_codes': qr_codes}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        dbclose(conn)

