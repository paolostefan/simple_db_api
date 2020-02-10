import configparser
import json
import os
import re
import sys
import time
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import mysql.connector
from mysql.connector import ProgrammingError


def json_serialize_datetime(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    raise TypeError(f"Type {type(obj)} is not serializable")


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


def extract_table_name_from(path: str):
    """
    Turns /table_name`+with+malicious+code+`/or/other/useless/path/elements into 'table_name'.

    :param path:
    :return:
    """
    if path[0] == '/':
        path = path[1:]

    if "/" in path:
        path = path[0:path.find('/')]

    if '`' in path:
        path = path[0:path.find('`')]

    return re.sub(r'[\W]+', '', path)


class ApiReqHandler(BaseHTTPRequestHandler):
    """
    Handler for HTTP requests
    """

    def do_GET(self):
        url = self.path
        parsed = urlparse(url)

        response = dict()
        status_code = 500  # pessimistic default
        try:
            if parsed.path == '/':
                response['results'] = self.server.get_table_names()
                status_code = 200
            else:
                table_name = extract_table_name_from(parsed.path)
                parameters = parse_qs(parsed.query) if parsed.query else {}
                if not table_name:
                    response['error'] = 'Please specify a table name'
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


class ApiWebServer(HTTPServer):
    cnx = None
    config = None
    db_options = None

    def __init__(self):
        """
        Read configuration file (./config.ini) and setup custom web handler.
        Don't start the web server yet.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, 'config.ini')
        if not os.path.isfile(config_path):
            print(f"*** FATAL: config file not found. Please create one at '{config_path}'")
            exit(1)

        config = configparser.RawConfigParser()
        config.read(config_path)

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

    def connect_db(self, db_options):
        # https://dev.mysql.com/doc/connector-python/en/connector-python-example-connecting.html

        try:
            self.cnx = mysql.connector.connect(**db_options)
        except Exception as e:
            self.log_message("Cannot connect to {}:{} MySQL db: {}", db_options['host'], db_options['port'], e)
            raise e

        self.log_message(
            f"Established connection to db {db_options['host']}:{db_options['port']}/{db_options['database']}")
        return self.cnx

    def get_table_names(self):

        if not self.cnx or not self.cnx.is_connected():
            self.connect_db(self.db_options)

        cursor = self.cnx.cursor()
        cursor.execute("SHOW TABLES;")
        raw_results = cursor.fetchall()
        cursor.close()

        # Turn list-like rows into flat strings
        results = [row[0] for row in raw_results]
        return results

    def do_query(self, table_name, params):

        if not self.cnx or not self.cnx.is_connected():
            self.connect_db(self.db_options)

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
        Start the web server. Don't connect to the db yet.
        :return:
        """
        try:
            self.log_message(f"Server started at http://{self.server_name}:{self.server_port}")
            self.serve_forever()
        except KeyboardInterrupt:
            pass

        self.log_message("Closing database connection...")
        self.cnx.close()

        self.log_message("Stopping webserver...")
        self.server_close()

        self.log_message("Server stopped.")

    @staticmethod
    def log_date_time_string():
        """Return the current time formatted for logging."""
        now = time.time()
        year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        return f"{day:02}/{month:02}/{year:04} {hh:02}:{mm:02}:{ss:02}"

    def log_message(self, format_str, *args):
        """
        Log an arbitrary message.

        Copied almost bit-to-bit from http.server.BaseHTTPRequestHandler.log_message

        The first argument, FORMAT, is a format string for the
        message to be logged.  If the format string contains
        any % escapes requiring parameters, they should be
        specified as subsequent arguments (it's just like
        printf!).

        The client ip and current date/time are prefixed to
        every message.
        """

        sys.stderr.write(f"{self.server_name} [{self.log_date_time_string()}] {format_str % args}\n")


if __name__ == '__main__':
    server = ApiWebServer()
    server.start()
