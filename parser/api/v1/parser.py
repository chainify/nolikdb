import os
from sanic import Blueprint
from sanic.response import json
from sanic.log import logger
import asyncio
import aiohttp
import requests
import psycopg2
import json as pjson
from psycopg2.extras import execute_values
import hashlib
from datetime import datetime
from time import time
from .errors import bad_request
import configparser
import uuid
import signal
import base58
import xml.etree.ElementTree as ET

config = configparser.ConfigParser()
config.read('config.ini')

parser = Blueprint('parser_v1', url_prefix='/parser')
dsn = {
    "user": os.environ['POSTGRES_USER'],
    "password": os.environ['POSTGRES_PASSWORD'],
    "database": os.environ['POSTGRES_DB'],
    "host": config['DB']['host'],
    "port": config['DB']['port'],
    "sslmode": config['DB']['sslmode'],
    "target_session_attrs": config['DB']['target_session_attrs']
}


class Parser:
    def __init__(self):
        self.height = 1
        self.last_block = None
        self.step = 5
        self.blocks_to_check = 5

        self.db_reconnects = 0
        self.db_max_reconnects = 10
        self.transactions_inserted = 0

        self.sql_data_transactions = []
        self.sql_data_proofs = []
        self.sql_data_tables = []
        self.sql_data_columns = []
        self.sql_data_values = []

    async def emergency_stop_loop(self, title, error):
        logger.info('Emergency loop stop request')
        logger.info('Reason: {}'.format(error))
        logger.info('Closing tasks')
        for task in asyncio.Task.all_tasks():
            task.cancel()

        logger.info('Stopping loop')
        loop = asyncio.get_running_loop()
        loop.stop()
        return bad_request(error)

    async def fetch_data(self, url, session):
        try:
            async with session.get(url) as response:
                data = await response.text()
                data = pjson.loads(data)
                cnfy_id = 'cnfy-{}'.format(str(uuid.uuid4()))

                for tx in data['transactions']:
                    if tx['type'] in [4] and tx['feeAssetId'] == os.environ['ASSET_ID']:
                        
                        attachment_base58 = base58.b58decode(tx['attachment']).decode('utf-8')
                        attachment = None
                        try:
                            attachment = requests.get('{0}:{1}/ipfs/{2}'.format(config['ipfs']['host'], config['ipfs']['port'], attachment_base58), timeout=2).text
                        except Exception as error:
                            logger.error('IPFS Error: {0}'.format(error))

                        if attachment == None:
                            logger.warning('CONTINUE ON IPFS HASH {0}'.format(attachment_base58) )
                            continue

                        attachment_hash = hashlib.sha256(attachment.encode('utf-8')).hexdigest()

                        root = ET.fromstring(attachment)
                        version = root.findall('version')[0].text if len(root.findall('version')) > 0 else None
                        blockchain = root.findall('blockchain')[0].text if len(root.findall('blockchain')) > 0 else None
                        network = root.findall('network')[0].text if len(root.findall('network')) > 0 else None
                        operations = root.findall('operations')[0] if len(root.findall('operations')) > 0 else []

                        if str(version) != str(os.environ['CDM_VERSION']):
                            continue
                        
                        operation_create = operations.findall('create')[0] if len(operations.findall('create')) > 0 else None
                        operation_insert = operations.findall('insert')[0] if len(operations.findall('insert')) > 0 else None
                        if (operation_create):
                            table_ciphertext = None
                            table_sha256hash = None
                            table = operation_create.findall('table')[0] if len(operation_create.findall('table')) > 0 else None
                            
                            recipient_public_key = None
                            recipient = operation_create.findall('recipient')[0] if len(operation_create.findall('recipient')) > 0 else None
                            if recipient:
                                recipient_public_key = recipient.findall('publickey')[0].text if len(recipient.findall('publickey')) > 0 else None
                                
                            if table:
                                table_ciphertext = table.findall('ciphertext')[0].text if len(table.findall('ciphertext')) > 0 else None
                                table_sha256hash = table.findall('sha256')[0].text if len(table.findall('sha256')) > 0 else None

                                self.sql_data_tables.append((
                                    table_sha256hash,
                                    tx['id'],
                                    table_ciphertext,
                                    recipient_public_key
                                ))

                            columns = operation_create.findall('columns')[0] if len(operation_create.findall('columns')) > 0 else None
                            if columns:
                                cols = columns.findall('column') if len(columns.findall('column')) > 0 else None
                                for col in cols:
                                    col_ciphertext = None
                                    col_sha256hash = None

                                    if col:
                                        col_ciphertext = col.findall('ciphertext')[0].text if len(col.findall('ciphertext')) > 0 else None
                                        col_sha256hash = col.findall('sha256')[0].text if len(col.findall('sha256')) > 0 else None

                                        self.sql_data_columns.append((
                                            col_sha256hash,
                                            table_sha256hash,
                                            col_ciphertext,
                                            recipient_public_key
                                        ))

                        if (operation_insert):
                            table_ciphertext = None
                            table_sha256hash = None
                            table = operation_insert.findall('table')[0] if len(operation_insert.findall('table')) > 0 else None

                            recipient_public_key = None
                            recipient = operation_insert.findall('recipient')[0] if len(operation_insert.findall('recipient')) > 0 else None
                            if recipient:
                                recipient_public_key = recipient.findall('publickey')[0].text if len(recipient.findall('publickey')) > 0 else None
                                
                            columns = operation_insert.findall('columns')[0] if len(operation_insert.findall('columns')) > 0 else None
                            if columns:
                                cols = columns.findall('column') if len(columns.findall('column')) > 0 else None
                                for col in cols:
                                    col_ciphertext = None
                                    col_sha256hash = None
                                    val_ciphertext = None
                                    val_sha256hash = None

                                    if col:
                                        col_ciphertext = col.findall('ciphertext')[0].text if len(col.findall('ciphertext')) > 0 else None
                                        col_sha256hash = col.findall('sha256')[0].text if len(col.findall('sha256')) > 0 else None
                                        
                                        value = col.findall('value')[0] if len(col.findall('value')) > 0 else None
                                        if value:
                                            val_ciphertext = value.findall('ciphertext')[0].text if len(value.findall('ciphertext')) > 0 else None
                                            val_sha256hash = value.findall('sha256')[0].text if len(value.findall('sha256')) > 0 else None
                                        
                                        self.sql_data_values.append((
                                            val_sha256hash,
                                            col_sha256hash,
                                            val_ciphertext,
                                            col_ciphertext,
                                            recipient_public_key
                                        ))
                                        print(self.sql_data_values)

                        tx_data = (
                            tx['id'],
                            data['height'],
                            tx['type'],
                            tx['sender'],
                            tx['senderPublicKey'],
                            tx['recipient'],
                            tx['amount'],
                            tx['assetId'],
                            tx['feeAssetId'],
                            tx['feeAsset'],
                            tx['fee'],
                            tx['attachment'],
                            tx['version'],
                            datetime.fromtimestamp(tx['timestamp'] / 1e3),
                            cnfy_id,
                            attachment_hash
                        )
                        
                        self.sql_data_transactions.append(tx_data)

                        for proof in tx['proofs']:
                            proof_id = 'proof-' + str(uuid.uuid4())
                            self.sql_data_proofs.append((tx['id'], proof, proof_id))

                       

        except asyncio.CancelledError:
            logger.info('Parser has been stopped')
            raise
        except Exception as error:
            logger.error('Fetching data error: {}'.format(error))
            pass
            # await self.emergency_stop_loop('Fetch data', error)

    async def save_data(self):
        conn = psycopg2.connect(**dsn)
        try:
            with conn:
                with conn.cursor() as cur:
                    if len(self.sql_data_transactions) > 0:
                        sql = """INSERT INTO transactions (
                            id,
                            height,
                            type,
                            sender,
                            sender_public_key,
                            recipient,
                            amount,
                            asset_id,
                            fee_asset_id,
                            fee_asset,
                            fee,
                            attachment,
                            version,
                            timestamp,
                            cnfy_id,
                            attachment_hash
                        ) VALUES %s ON CONFLICT (id) DO UPDATE SET height = EXCLUDED.height"""
                        execute_values(cur, sql, self.sql_data_transactions)
                        if cur.rowcount > 0:
                            self.transactions_inserted += cur.rowcount

                        sql = """INSERT INTO proofs (tx_id, proof, id) VALUES %s ON CONFLICT DO NOTHING"""
                        execute_values(cur, sql, self.sql_data_proofs)

                        sql = """INSERT INTO tables (
                            hash,
                            tx_id,
                            ciphertext,
                            recipient
                        ) VALUES %s ON CONFLICT DO NOTHING"""
                        execute_values(cur, sql, self.sql_data_tables)

                        if len(self.sql_data_columns) > 0:
                            sql = """INSERT INTO columns (
                                hash,
                                table_hash,
                                ciphertext,
                                recipient
                            ) VALUES %s ON CONFLICT DO NOTHING"""
                            execute_values(cur, sql, self.sql_data_columns)

                        print('self.sql_data_values', self.sql_data_values)
                        if len(self.sql_data_values) > 0:
                            sql = """INSERT INTO values (
                                val_hash,
                                col_hash,
                                val_ciphertext,
                                col_ciphertext,
                                recipient
                            ) VALUES %s ON CONFLICT DO NOTHING"""
                            execute_values(cur, sql, self.sql_data_values)

                    conn.commit()
                    logger.info('Saved {0} transactions'.format(self.transactions_inserted))

        except psycopg2.IntegrityError as error:
            logger.info('Error', error)
            pass
        except asyncio.CancelledError:
            logger.info('Parser has been stopped')
            raise
        except Exception as error:
            logger.info('Height: {}'.format(self.height))
            logger.error('Batch insert error: {}'.format(error))
            await self.emergency_stop_loop('Batch insert error', error)
        finally:
            self.transactions_inserted = 0
            self.sql_data_transactions = []
            self.sql_data_proofs = []
            self.sql_data_tables = []
            self.sql_data_columns = []
            self.sql_data_values = []

    async def start(self):
        conn = None
        try:
            conn = psycopg2.connect(**dsn)
        except psycopg2.OperationalError as error:
            logger.error('Postgres Engine Error:', error)
            await self.emergency_stop_loop('No conn error', 'Error on connection to Postgres Engine')

        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT max(height) FROM transactions")
                    max_height = cur.fetchone()

                    if max_height and max_height[0]:
                        if max_height[0] > self.blocks_to_check:
                            self.height = max_height[0] - self.blocks_to_check

                    if os.environ['START_HEIGHT']:
                        start_height = int(os.environ['START_HEIGHT'])
                        if self.height < start_height:
                            self.height = start_height

        
        except Exception as error:
            logger.error('Max height request error: {}'.format(error))
            await self.emergency_stop_loop('Max height request error', error)

        while True:
            try:
                req = requests.get('{0}/node/status'.format(os.environ['NODE_URL']))
                data = req.json()
                self.last_block = int(data['blockchainHeight'])

                with conn:
                    with conn.cursor() as cur:
                        if self.height > self.last_block:
                            cur.execute("""
                                DELETE FROM transactions WHERE height > '{height}'
                            """.format(
                                height=self.last_block
                            ))
                            self.height = self.last_block
                            conn.commit()

            except Exception as error:
                await self.emergency_stop_loop('Waves node is not responding', error)

            logger.info('Start height: {}, last block: {}'.format(self.height, self.last_block))
            logger.info('-' * 40)
            try:
                async with aiohttp.ClientSession() as session:
                    try:
                        while self.height < self.last_block:
                            t0 = time()
                            batch = self.height + self.step
                            if self.height + self.step >= self.last_block:
                                batch = self.last_block + 1

                            batch_range = (self.height, batch)
                            tasks = []
                            for i in range(batch_range[0], batch_range[1]):
                                url = '{0}/blocks/at/{1}'.format(os.environ['NODE_URL'], self.height)
                                task = asyncio.create_task(self.fetch_data(url, session))
                                tasks.append(task)
                                self.height += 1
                            logger.info('Height range {0} - {1}'.format(batch_range[0], batch_range[1]))
                            await asyncio.gather(*tasks)
                            await self.save_data()
                            logger.info('Parsing time: {0} sec'.format(time() - t0))
                            logger.info('-' * 40)

                    except asyncio.CancelledError:
                        logger.info('Parser stopping...')
                        raise
                    except Exception as error:
                        logger.error('Blocks session cycle error on height {0}: {1}'.format(self.height, error))
                        await self.emergency_stop_loop('Blocks session cycle error', error)

            except asyncio.CancelledError:
                logger.info('Parser has been stopped')
                raise
            except Exception as error:
                logger.error('Request blocks cycle error: {0}'.format(error))
                await self.emergency_stop_loop('Request blocks cycle', error)
            finally:
                self.height = self.height - self.blocks_to_check
                await asyncio.sleep(2)


controls = Parser()

@parser.listener('after_server_start')
def autostart(app, loop):
    loop.create_task(controls.start())
    logger.info('Autostart Success!')
    logger.info('CDM Version: {0}'.format(os.environ['CDM_VERSION']))

@parser.listener('after_server_stop')
def gentle_exit(app, loop):
    logger.info('Killing the process')
    os.kill(os.getpid(), signal.SIGKILL)

@parser.route('/healthcheck', methods=['GET'])
def container_healthcheck(request):
    return json({"action": "healthcheck", "status": "OK"})
