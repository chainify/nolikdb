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

columns = Blueprint('columns_v1', url_prefix='/columns')

class Columns(HTTPMethodView):
    @staticmethod
    def get(request, public_key):
        data = get_columns(public_key)
        return json(data, status=200)

def get_columns(public_key):
    conn = psycopg2.connect(**dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT c.hash, c.ciphertext, t.hash, t.ciphertext
                    FROM columns c
                    LEFT JOIN tables t ON t.hash = c.table_hash
                    WHERE c.recipient='{public_key}'
                """.format(
                    public_key=public_key
                )
                cur.execute(sql)
                columns = cur.fetchall()

    except Exception as error:
        return bad_request(error)
    
    return [{
        'columnHash': col[0],
        'columnCiphertext': col[1],
        'tableHash': col[2],
        'tableCiphertext': col[3]
    } for col in columns]

columns.add_route(Columns.as_view(), '/<public_key>')