#   Python3 Flask Relay API for CoinAPI.io

# --------------------------------------------------------
#   Monty Dimkpa - Published: May 14, 2020
# --------------------------------------------------------

# --------------------------------------------------------
# The Relay API serves as a relay between CoinAPI.io, our
# Postgres DB and the React front-end. A Node Scheduler
# fires a relay endpoint on this API at
# intervals to pull raw JSON data from CoinAPI.io which will
# be transformed into the required format and stored in our
# Postgres DB. The front end fires a second relay endpoint
# on this API on demand, to pull data for hydrating the views.
# --------------------------------------------------------

# ------------------------ INIT -------------------------------
import os
import json
import datetime
import requests as http
from flask_cors import CORS
from flask import Flask, request, Response
import psycopg2
import urllib.parse as urlparse

# API version
API_Version = 1

# instantiate Flask object
app = Flask(__name__)

# Cross-Origin-Allow-*
CORS(app)

# ------------------------ General Settings -------------------------------

true = True
false = False
null = None
# DB Store Event Counter
event_counter = 0
# API Home and ROOT
API_HOME = os.getcwd()
if "\\" in API_HOME:
    slash = "\\"
else:
    slash = "/"
API_HOME+=slash
# initialize time_start
time_start = "2016-01-01T00:00:00"

# ------------------------ Helper Functions -------------------------------

def Settings():
    """
    Retrieve App Settings
    """
    settings_file = API_HOME+"settings.json"
    p = open(settings_file, "rb+")
    settings = json.loads(p.read())
    p.close()
    return settings

def responsify(status, message, data={}):
    """
    Send Formatted HTTP Responses
    """
    code = int(status)
    a_dict = {"data": data, "message": message, "code": code}
    try:
        return Response(json.dumps(a_dict), status=code, mimetype='application/json')
    except:
        return Response(str(a_dict), status=code, mimetype='application/json')

def plus_one(highest_time):
    global time_start
    """
    increment highest_time by 1 second and set as time_start
    """
    time_start = (datetime.datetime.fromisoformat(highest_time.split(".")[0])+datetime.timedelta(0,0,0,0,1)).isoformat()
    return null

def isValidSecurityKey(key, mode):
    # check valid security key
    return key == Settings()["relay_api"]["security_key_relay_%s" % mode]

def symbol_id(data, explicit=false):
    # return matching symbol_id on `symbol` table
    if not explicit:
        Symbol = data["symbol_id"].split("_")[2]
    else:
        Symbol = data
    return ["BTC","ETH","XRP","LTC"].index(Symbol)+1

def transform(dataset):
    global time_start, highest_time
    """
    Data transformation hub: transform data to SQL and update time_start
    """
    def UTC_drop_Z(utc_z):
        # drop Z from UTC format
        return utc_z.split('Z')[0]
    def to_sql(data):
        global highest_time
        # transform data to SQL INSERT query
        sql = "INSERT INTO symbol_data ( symbol_id, time_coinapi, taker_side, price, size ) VALUES ( %s );" % ",".join([ str(symbol_id(data)), "'%s'" % data["time_coinapi"], "'%s'" % data["taker_side"], str(data["price"]), str(data["size"]) ])
        # update highest_time
        this_time = UTC_drop_Z(data["time_coinapi"])
        if this_time > highest_time:
            highest_time = this_time
        return sql
    # current highest_time
    highest_time = time_start
    # get SQL insert statements from data
    sql_inserts = list(map(to_sql, dataset))
    # set next time_start as plus 1 of highest_time
    plus_one(highest_time)
    return sql_inserts

def new_conn():
    """
    return a new DB connection object
    """
    url = urlparse.urlparse(Settings()["postgres"]["uri"])
    dbname = url.path[1:]
    user = url.username
    password = url.password
    host = url.hostname
    port = url.port
    conn = psycopg2.connect(dbname=dbname,user=user,password=password,host=host,port=port)
    return conn

# ------------------------ Routes -------------------------------

# RELAY-IN
@app.route("/relay-api/v%s/relay-in" % API_Version, methods=["GET"])
def do_relay_in():
    try:
        # Security Check
        if isValidSecurityKey(request.headers.get("Authorization"), "in"):
            try:
                # retrieve symbol requested
                Symbol = request.args.get("Symbol")
                # check valid symbol
                if Symbol in ["BTC", "ETH", "XRP", "LTC"]:
                    # call CoinAPI.io with incremental_update setting: time_start
                    settings = Settings()
                    dataset = http.get(settings["coinapi.io"]["api_base_url"] % (Symbol, time_start), headers=settings["coinapi.io"]["headers"]).json()
                    if dataset:
                        # only push if there is new incremental data
                        # transform dataset to SQL insert statements
                        sql_inserts = transform(dataset)
                        # create connection object
                        conn = new_conn()
                        # get cursor
                        cursor = conn.cursor(); cursor.execute('BEGIN')
                        # do batch insert
                        outputs = []
                        for sql_insert in sql_inserts:
                            cursor.execute("BEGIN")
                            outputs.append(cursor.execute(sql_insert))
                            cursor.execute("COMMIT")
                        # close connection
                        conn.close()
                        # destroy connection object
                        del conn
                        # return outputs
                        return responsify(201, "Successful", {"processed": len(outputs)})
                    else:
                        # No new incremental data
                        return responsify(204, "No Content", {})
                else:
                    # invalid Symbol
                    return responsify(400, "Bad Request: Invalid Symbol", {})
            except:
                # No Symbol sent
                return responsify(400, "Bad Request: Check Symbol Parameter", {})
        else:
            # no valid security key provided
            return responsify(401, "Unauthorized Access", {})
    except:
        # no valid security key provided
        return responsify(401, "Unauthorized Access", {})

# RELAY-OUT
@app.route("/relay-api/v%s/relay-out" % API_Version, methods=["GET"])
def do_relay_out():
    try:
        # Security Check
        if isValidSecurityKey(request.headers.get("Authorization"), "out"):
            try:
                # retrieve symbol requested
                Symbol = request.args.get("Symbol")
                # check valid symbol
                if Symbol in ["BTC", "ETH", "XRP", "LTC"]:
                    # fetch all matching data for Symbol
                    sql_query = "SELECT * from symbol_data WHERE symbol_data.symbol_id = %d" % symbol_id(Symbol, true)
                    # create connection object
                    conn = new_conn()
                    # get cursor
                    cursor = conn.cursor(); cursor.execute('BEGIN')
                    # run query; get data
                    cursor.execute(sql_query)
                    data = cursor.fetchall()
                    # close connection
                    conn.close()
                    # destroy connection object
                    del conn
                    # return records
                    return responsify(200, "Successful", {"records": data})
                else:
                    # invalid Symbol
                    return responsify(400, "Bad Request: Invalid Symbol", {})
            except:
                # No Symbol sent
                return responsify(400, "Bad Request: Check Symbol Parameter", {})
        else:
            # no valid security key provided
            return responsify(401, "Unauthorized Access", {})
    except:
        # no valid security key provided
        return responsify(401, "Unauthorized Access", {})


if __name__ == "__main__":
    # this multi-threaded local server will use Gunicorn as a proxy on Heroku with at least 2 workers
    app.run(host="localhost", port=5000, threaded=True)
