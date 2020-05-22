## Data Engineering Test (Backend - Relay API) - Monty Dimkpa

### Technologies used

Heroku (containers and Postgres DB), Python (Relay API)

### Architecture

The Relay API runs on a container (dyno) on Heroku

### DB Structure (Table Relationships)

```
CREATE TABLE symbol (
  symbol_id serial PRIMARY KEY,
  code VARCHAR (3) UNIQUE NOT NULL
);

CREATE TABLE symbol_data (
  symbol_data_id serial PRIMARY KEY,
  symbol_id integer NOT NULL,
  time_coinapi VARCHAR (30) NOT NULL,
  taker_side VARCHAR (10) NOT NULL,
  price FLOAT (10) NOT NULL,
  size FLOAT (10) NOT NULL,
  CONSTRAINT symbol_data_symbol_id_fkey FOREIGN KEY (symbol_id)
    REFERENCES symbol (symbol_id) MATCH SIMPLE
    ON UPDATE NO ACTION ON DELETE NO ACTION
);
```

### Operation - Relay API

The Relay API supports two principal operations: **Relay-In** and **Relay-Out**.

#### Relay-In

This is a scheduled process where an endpoint is fired to pull historical crypto data from CoinAPI.io; the data is processed and stored in a Postgres DB on Heroku.

#### Relay-Out

This is an on-demand process where crypto historical data is pulled from the DB and sent to the Front End.

#### Security

The Relay API is secured for both relay-in and relay-out operations, as a secure Authorization key is required for both steps and only the designated scheduler and Front-End can consume the API.

#### API Reference

##### Relay-In

```
GET - https://data-eng-test.herokuapp.com/relay-api/v1/relay-in?Symbol=SYMBOL - Headers: Authorization

201-Response: { code : 201, message : "Successful", data : { "processed" : records }  }
204-Response: { code : 204, message : "No Content", data : { }  }
401-Response: { code: 401, message : "Unauthorized Access", data : { }}
400-Response: { code: 400, message : "Bad Request: Check Symbol Parameter", data : { }}
400-Response: { code: 400, message : "Bad Request: Invalid Symbol", data : { }}

```

##### Relay-Out

```
GET - https://data-eng-test.herokuapp.com/relay-api/v1/relay-out?Symbol=SYMBOL - Headers: Authorization

200-Response: { code : 200, message : "Successful", data : { "records" : records }  }
401-Response: { code: 401, message : "Unauthorized Access", data : { }}
400-Response: { code: 400, message : "Bad Request: Check Symbol Parameter", data : { }}
400-Response: { code: 400, message : "Bad Request: Invalid Symbol", data : { }}

```
