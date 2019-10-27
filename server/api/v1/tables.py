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

tables = Blueprint('tables_v1', url_prefix='/tables')

class Tables(HTTPMethodView):
    @staticmethod
    def get(request, public_key):
        data = get_tables(public_key)
        return json(data, status=200)

def get_tables(public_key):
    conn = psycopg2.connect(**dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                sql = """
                    SELECT t.hash, t.ciphertext FROM tables t
                    WHERE recipient='{public_key}'
                """.format(
                    public_key=public_key
                )
                cur.execute(sql)
                tables = cur.fetchall()

                sql = """
                    SELECT t.hash, t.ciphertext FROM tables t
                    WHERE recipient='{public_key}'
                """.format(
                    public_key=public_key
                )
                cur.execute(sql)
                tables = cur.fetchall()

    except Exception as error:
        return bad_request(error)
    
    return [{
        'hash': table[0],
        'ciphertext': table[1]
    } for table in tables]

tables.add_route(Tables.as_view(), '/<public_key>')