# �۽���� runserver.py
from flask import Flask
from app_user import app_user, init_bcrypt
from app_owner import app_owner, init_bcrypt
from app_franchise import app_franchise
from app_store import app_store
from app_admin import app_admin
from app_order import app_order


# �ۼ��� �ʱ�ȭ
app = Flask(__name__)


# �� Blueprint�� URL ���ξ�� �Բ� ���
app.register_blueprint(app_user, url_prefix='/user')
app.register_blueprint(app_owner, url_prefix='/owner')
app.register_blueprint(app_franchise, url_prefix='/franchise')
app.register_blueprint(app_store, url_prefix='/store')
app.register_blueprint(app_admin, url_prefix='/admin')
app.register_blueprint(app_order, url_prefix='/order')


# Bcrypt �ʱ�ȭ
init_bcrypt(app)

if __name__ == "__main__":
    app.run(app, host='0.0.0.0', port='8000', debug=True)
    # host : ���� IP, 0.0.0.0�� ���� ȣ��Ʈ�� ��Ī��
    # port : �������� 8000��Ʈ���� �����ϰڴٴ� ����
    # debug : ���� ����θ� ���������� �͹̳�â���� ���� �α� �������