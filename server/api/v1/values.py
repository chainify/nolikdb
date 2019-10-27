import os
import psycopg2
from sanic import Blueprint
from sanic.views import HTTPMethodView
from sanic.response import json
from .errors import bad_request
import configparser
import base58

config = configparser.ConfigParser()
config.read('config.ini')

dsn = {
    "user": os.environ['POSTGRES_USER'],
    "password": os.environ['POSTGRES_PASSWORD'],
    "database": os.environ['POSTGRES_DB'],
    "host": config['DB']['host'],
    "port": config['DB']['port'],
    "sslmode": config['DB']['sslmode'],
    "target_session_attrs": config['DB']['target_session_attrs']
}

values = Blueprint('values_v1', url_prefix='/values')

class Values(HTTPMethodView):
    @staticmethod
    def get(request, public_key):
        data = get_values(public_key)
        return json(data, status=200)

def get_values(public_key):
    conn = psycopg2.connect(**dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT v.col_hash, v.col_ciphertext, v.val_hash, v.val_ciphertext FROM values v
                    WHERE v.recipient='{public_key}'
                """.format(
                    public_key=public_key
                )
                cur.execute(sql)
                values = cur.fetchall()

    except Exception as error:
        return bad_request(error)
    
    return [{
        'columnHash': val[0],
        'columnCiphertext': val[1],
        'valueHash': val[2],
        'valueCiphertext': val[3]
    } for val in values]

values.add_route(Values.as_view(), '/<public_key>')