# �ֹ��� ������ ���õ� ���Ʈ���� ��Ƶ� ��� ���� app_order.py
import os
import pymysql
import uuid
import logging

from flask_cors import CORS
from flask import Blueprint, jsonify, request
from marshmallow import Schema, fields, post_load, ValidationError
from dbconn import dbcon, dbclose


app_order = Blueprint('order', __name__)
CORS(app_order)


# �α� ����
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# QR��ĵ ��Ű��
class QRScanSchema(Schema):
    ownerid = fields.String(required=True)
    tablenumber = fields.Integer(required=True)
    userid = fields.String(required=False)  # userid ��� �������

    @post_load
    def make_qrscan(self, data, **kwargs):
        return QRScan(**data)

class MenuItemSchema(Schema):
    productid = fields.Integer()
    productname = fields.String()
    price = fields.String()  # price�� ���ڿ��� ����
    imageurl = fields.String()
    category = fields.String()
    description = fields.String()

class MenuResponseSchema(Schema):
    storeid = fields.String()
    tablenumber = fields.Integer()
    menu_items = fields.List(fields.Nested(MenuItemSchema))
    orderid = fields.String()

class PaymentSchema(Schema):
    merchant_uid = fields.String(required=False)  # Ŭ���̾�Ʈ�� �����ִ� �ֹ���ȣ
    amount = fields.Decimal(required=False)  # �� ���� �ݾ�
    buyer_email = fields.String(required=False)
    buyer_name = fields.String(required=False)  # ����� ���̵�
    buyer_tel = fields.String(required=False)  # ����� ��ȭ��ȣ
    buyer_addr = fields.String(required=False)  # ����� �ּ�
    buyer_postcode = fields.String(required=False)  # ��?��
    pay_method = fields.String(required=False)  # �������
    pg = fields.String(required=False)  # ��?��
    order_details = fields.Dict(required=True)  # ��ųʸ��� ����
    userid = fields.String(required=True)  # ����� ���̵�
    orderid = fields.String(required=True)  # �ֹ� ���̵�

# QR ��ĵ Ŭ���� ������
class QRScan:
    def __init__(self, ownerid, tablenumber, userid=None): # userid�� ���������� ó��
        self.ownerid = ownerid
        self.tablenumber = tablenumber
        self.userid = userid


qr_scan_schema = QRScanSchema()
menu_response_schema = MenuResponseSchema()
payment_schema = PaymentSchema()


# QR��ĵ ���Ʈ
# ���Ը޴� ��ȯ & orders���̺� ���ڵ� ����
@app_order.route('/scan', methods=['POST'])
def scan_qr():
    json_data = request.get_json()
    logger.info(f"Received JSON data: {json_data}")
    
    try:
        data = qr_scan_schema.load(json_data)
    except ValidationError as err:
        logger.error(f"Validation error: {err.messages}")
        return jsonify(err.messages), 400
    
    ownerid = data.ownerid
    tablenumber = data.tablenumber
    userid = data.userid
    logger.info(f"Parsed data - ownerid: {ownerid}, tablenumber: {tablenumber}, userid: {userid}")

    conn = dbcon()
    if not conn:
        logger.error("Database connection failed")
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            query_menu = """
                SELECT productid, productname, price, imageurl, category, description FROM storemenu WHERE storeid = %s
            """
            cursor.execute(query_menu, (ownerid,))
            menu_items = cursor.fetchall()
            logger.info(f"Fetched menu items: {menu_items}")

            if not menu_items:
                logger.warning(f"No menu items found for storeid: {ownerid}")
                return jsonify({"error": "No menu items found for the given storeid"}), 404

            # ���ڿ� ���ݿ��� �޸��� �����ϰ� ���������� ��ȯ
            for item in menu_items:
                item['price'] = int(item['price'].replace(',', ''))

            # orderid ����
            orderid = str(uuid.uuid4())
            logger.info(f"Generated orderid: {orderid}")

            # orders ���̺� ���ڵ� ����
            query_order = """
                INSERT INTO orders (orderid, ownerid, tablenumber, userid, order_status)
                VALUES (%s, %s, %s, %s, 0)
            """
            cursor.execute(query_order, (orderid, ownerid, tablenumber, userid))
            conn.commit()
            logger.info("Inserted new order into orders table")

            menu_response = {
                "storeid": ownerid,
                "tablenumber": tablenumber,
                "menu_items": menu_items,
                "orderid": orderid
            }

            result = menu_response_schema.dump(menu_response)

            return jsonify(result)

    except pymysql.MySQLError as e:
        logger.error(f"Query failed: {e}")
        return jsonify({"error": "Query failed"}), 500

    finally:
        dbclose(conn)


# ���� ���� ���� ���Ʈ
@app_order.route('/payments', methods=['POST'])
def order_payment():
    json_data = request.get_json()

    logger.info(f"Received JSON data: {json_data}")

    try:
        data = payment_schema.load(json_data)
        logger.info(f"Parsed data: {data}")
    except ValidationError as err:
        logger.error(f"Validation error: {err.messages}")
        return jsonify(err.messages), 400

    order_details = data['order_details']
    userid = data.get('userid')
    orderid = data.get('orderid')
    merchant_uid = data.get('merchant_uid')
    amount = order_details['amount']  # order_details���� amount ����
    buyer_email = data.get('buyer_email')
    buyer_name = data.get('buyer_name')
    buyer_tel = data.get('buyer_tel')
    buyer_addr = data.get('buyer_addr')
    buyer_postcode = data.get('buyer_postcode')
    pay_method = data.get('pay_method')
    pg = data.get('pg')

    if not userid or not orderid:
        logger.error("User ID and Order ID are required")
        return jsonify({"error": "User ID and Order ID are required"}), 400

    menu_items = order_details['menu_items']

    conn = dbcon()
    if not conn:
        logger.error("Database connection failed")
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # Ʈ����� ����
            conn.begin()
            logger.info("Transaction started")

            # orders ���̺��� order_status�� 0�� ���ڵ带 orderid�� ��ȸ�Ͽ� ownerid Ȯ��
            query_get_order = """
                SELECT ownerid FROM orders WHERE order_status = 0 AND orderid = %s LIMIT 1
            """
            cursor.execute(query_get_order, (orderid,))
            result = cursor.fetchone()
            if result:
                ownerid = result['ownerid']
                logger.info(f"Owner ID found: {ownerid}")
            else:
                logger.error("Order not found or already processed")
                return jsonify({"error": "Order not found or already processed"}), 404

            # �ֹ� �� ���� ����
            query_order_details = """
                INSERT INTO order_details (orderid, menu_name, quantity, menu_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """
            for item in menu_items:
                cursor.execute(query_order_details, (
                    orderid,
                    item['productname'],
                    int(item.get('quantity', 1)),
                    int(item['price']),
                    amount
                ))

            # �ֹ� ���� ������Ʈ (���� �Ϸ�� ����)
            query_update_order = """
                UPDATE orders SET order_status = %s, ordertime = %s WHERE orderid = %s
            """
            cursor.execute(query_update_order, (1, merchant_uid, orderid))
            logger.info(f"Order status updated for order ID: {orderid}")

            # ���� ���� ����
            query_payment = """
                INSERT INTO order_payments (
                    orderid, merchant_uid, amount, buyer_email, buyer_name, buyer_tel, 
                    buyer_addr, buyer_postcode, pay_method, pg
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_payment, (
                orderid, merchant_uid, amount, buyer_email, buyer_name, buyer_tel, 
                buyer_addr, buyer_postcode, pay_method, pg
            ))
            logger.info("Payment information saved")

            # Ʈ����� Ŀ��
            conn.commit()
            logger.info("Transaction committed")

            return jsonify({'message': 'Payment information saved successfully', 'orderid': orderid}), 200

    except pymysql.MySQLError as e:
        # Ʈ����� �ѹ�
        conn.rollback()
        logger.error(f"Query failed: {e}")
        return jsonify({"error": "Query failed", "details": str(e)}), 500

    finally:
        dbclose(conn)
        logger.info("Database connection closed")


class StoreServeListSchema(Schema):
    ownerid = fields.String(required=True)

store_serve_list_schema = StoreServeListSchema()


# ���������� ����� �ֹ���Ȳ ��ȸ ���Ʈ
@app_order.route('/serve_list', methods=['POST'])
def store_serve_list():
    json_data = request.get_json()

    try:
        data = store_serve_list_schema.load(json_data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    ownerid = data['ownerid']

    conn = dbcon()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # orders ���̺��� order_status�� 1�̰� ownerid�� ��ġ�ϴ� ��� orderid ��ȸ
            query_get_orders = """
                SELECT orderid, tablenumber, staffcall, ordertime FROM orders WHERE order_status = 1 AND ownerid = %s
            """
            cursor.execute(query_get_orders, (ownerid,))
            orders = cursor.fetchall()

            if not orders:
                return jsonify({"error": "No orders found"}), 404

            order_details_list = []
            for order in orders:
                orderid = order['orderid']
                tablenumber = order['tablenumber']
                staffcall = order['staffcall']
                ordertime = order['ordertime']

                # order_details ���̺��� �ش� orderid�� ��� ���ڵ� ��ȸ
                query_get_order_details = """
                    SELECT menu_name, quantity, total_price, menu_price FROM order_details WHERE orderid = %s
                """
                cursor.execute(query_get_order_details, (orderid,))
                order_details = cursor.fetchall()

                # order_payments ���̺��� �ش� orderid�� ���� ���� ��ȸ
                query_get_payment_info = """
                    SELECT pg, pay_method FROM order_payments WHERE orderid = %s
                """
                cursor.execute(query_get_payment_info, (orderid,))
                payment_info = cursor.fetchone()

                if order_details:
                    order_info = {
                        "orderid": orderid,
                        "tablenumber": tablenumber,
                        "staffcall": staffcall,
                        "ordertime": ordertime,
                        "order_details": order_details
                    }
                    if payment_info:
                        order_info.update({
                            "pg": payment_info['pg'],
                            "pay_method": payment_info['pay_method']
                        })
                    order_details_list.append(order_info)

            return jsonify(order_details_list), 200

    except pymysql.MySQLError as e:
        return jsonify({"error": "Query failed", "details": str(e)}), 500

    finally:
        dbclose(conn)


# �����Ϸ� ���Ʈ
@app_order.route('/serve_done', methods=['POST'])
def store_serve_done():
    json_data = request.get_json()

    logger.info(f"Received JSON data: {json_data}")

    orderid = json_data.get('orderid')
    
    if not orderid:
        logger.error("Order ID is required")
        return jsonify({"error": "Order ID is required"}), 400

    conn = dbcon()
    if not conn:
        logger.error("Database connection failed")
        return jsonify({"error": "Database connection failed"}), 500

    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            # orders ���̺��� order_status�� 3���� ������Ʈ
            query_update_order = """
                UPDATE orders SET order_status = %s WHERE orderid = %s
            """
            cursor.execute(query_update_order, (3, orderid))
            logger.info(f"Order status updated to 3 for order ID: {orderid}")

            # Ʈ����� Ŀ��
            conn.commit()
            logger.info("Transaction committed")

            return jsonify({'message': 'Order status updated successfully', 'orderid': orderid}), 200

    except pymysql.MySQLError as e:
        # Ʈ����� �ѹ�
        conn.rollback()
        logger.error(f"Query failed: {e}")
        return jsonify({"error": "Query failed", "details": str(e)}), 500

    finally:
        dbclose(conn)
        logger.info("Database connection closed")