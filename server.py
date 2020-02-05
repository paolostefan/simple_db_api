import configparser
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import date, datetime

import mysql.connector
from mysql.connector import ProgrammingError


def json_serialize_datetime(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    raise TypeError(f"Type {type(obj)} is not serializable")


class ApiReqHandler(BaseHTTPRequestHandler):

    @staticmethod
    def get_table_name(path: str):
        if '/' not in path:
            return path

        if path[0] == '/':
            path = path[1:]

        if "/" in path:
            path = path[0:path.find('/')]

        return path

    def do_GET(self):
        url = self.path
        parsed = urlparse(url)
        table_name = self.get_table_name(parsed.path)
        parameters = parse_qs(parsed.query) if parsed.query else {}

        response = dict()
        status_code = 500  # pessimismo
        try:
            if not table_name:
                response['error'] = 'Please specify a non-null path'
                status_code = 400
            else:
                response['results'] = self.server.do_query(table_name, parameters)
                status_code = 200
        except ProgrammingError as e:
            response['error'] = e.msg
            response['errno'] = e.errno
            response['sqlstate'] = e.sqlstate
        except Exception as e:
            response['error'] = str(e)

        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(json.dumps(response, default=json_serialize_datetime), "utf-8"))


OPERATORS = {
    'eq': '=',
    'ne': '<>',
    'gt': '>',
    'lt': '<',
    'gte': '>=',
    'lte': '<',
}


def parse_sql_filter(sql_filter: str) -> str:
    sep_count = sql_filter.count(':')
    if not sep_count:
        raise ValueError("Filter must be in the form column:operator[:value]")

    if sep_count == 1:
        operator: str
        (col, operator) = sql_filter.split(':')
        operator = operator.lower()
        if operator != 'null' and operator != 'not_null':
            raise ValueError('Unknown unary operator')
        return f"`{col}` IS NULL" if operator == 'null' else f"`{col}` IS NOT NULL"

    else:
        (col, operator, value) = sql_filter.split(':')
        operator = operator.lower()
        if operator not in OPERATORS:
            raise ValueError('Unknown binary operator')

        return f"`{col}` {OPERATORS[operator]} '{value}'"


class ApiWebServer(HTTPServer):
    cnx = None
    config = None
    db_options = None

    def __init__(self):
        """
        Read configuration file (./config.ini) and setup custom web handler.
        """
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        config = configparser.ConfigParser()
        config.read(os.path.join(BASE_DIR, 'config.ini'))

        hostname = config.get('web', 'hostname', fallback='localhost')
        port = config.getint('web', 'port', fallback=8080)

        self.config = config

        #  database
        self.db_options = {
            'user': config['database']['user'],
            'password': config['database']['password'],
            'host': config.get('database', 'server', fallback='127.0.0.1'),
            'port': config.getint('database', 'port', fallback=3306),
            'database': config['database']['database']
        }

        super(ApiWebServer, self).__init__((hostname, port), ApiReqHandler)

    def do_query(self, table_name, params):
        cursor = self.cnx.cursor()
        where_clause = '1'

        if 'filter' in params:
            where_clauses = []
            for sql_filter in params['filter']:
                where_clauses.append(parse_sql_filter(sql_filter))
            where_clause = ' AND '.join(where_clauses)

        order_clause = ''
        if 'order' in params:
            sort_clauses = []
            for sorting in params['order']:
                sort_col = sorting
                sort_dir = 'ASC'
                if sort_col[0] == '-':
                    sort_dir = 'DESC'
                    sort_col = sort_col[1:]
                sort_clauses.append(f"`{sort_col}` {sort_dir}")

            order_clause = f"ORDER BY {','.join(sort_clauses)}"

        offset = params['offset'][0] if 'offset' in params else 0
        limit = params['limit'][0] if 'limit' in params else 20
        limit_clause = f"LIMIT {offset}, {limit}"

        query = f"SELECT * FROM `{table_name}` WHERE {where_clause} {order_clause} {limit_clause}"

        cursor.execute(query)
        raw_results = cursor.fetchall()
        columns = cursor.column_names
        cursor.close()

        # Turn list-like rows into dicts
        results = [dict(zip(columns, row)) for row in raw_results]

        return results

    def start(self):
        """
        Connect to the db and start web server
        :return:
        """
        db_conf = self.db_options
        # https://dev.mysql.com/doc/connector-python/en/connector-python-example-connecting.html
        try:
            self.cnx = mysql.connector.connect(**db_conf)
        except Exception as e:
            print(e)
            exit(1)
        print(f"Established connection to db {db_conf['host']}:{db_conf['port']}/{db_conf['database']}")

        try:
            print(f"Server started at http://{self.server_name}:{self.server_port}")
            self.serve_forever()
        except KeyboardInterrupt:
            pass

        print("Closing database connection...")
        self.cnx.close()
        print("Stopping webserver...")
        self.server_close()
        print("Server stopped.")


if __name__ == '__main__':
    server = ApiWebServer()
    server.start()
