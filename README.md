# Simple Python db API

Quick and easy Python (3.6+) webserver exposing a read-only database API.

## The problem

You need to retrieve data from a database using a web service, and you **don't want** or 
**don't have the time** to develop a full-blown RESTful API and configure a webserver to serve it. 

## This repo's solution

The `server.py` script does exactly this: it fires up a basic web server on port 8080,
making it possible to query the tables of the configured database. For security reasons 
(and to keep it simple :) the server will only execute `SELECT` queries.

## Installation

1. Clone the repo and cd into it

2. Create a python3 virtualenv 

    ```
   python3 -m virtualenv venv -p python3
    ```
   
   If you don't have **virtualenv** installed, you may need to run `sudo apt install python3-virtualenv` 
   (on Debian/Ubuntu or Debian-based distros) or the corresponding command to install it. 
   

3. Activate the virtualenv and install required packages

    ```
   source venv/bin/activate
   pip install -m requirements.txt
    ```


2. Create a config.ini file, preferably by copying the sample file provided:

    `cp ./config.ini-sample ./config.ini`

3. Edit `config.ini`, replacing the defaults with your db connection data. Depending on your network config, you may 
   need to change the web/host and/or port on which the webserver will run. 

4. Run `python3 server.py`. 

That's it! If everything went well, you will see a message like this in the console:

````
Server started at http://localhost:8080
````

and you'll be ready to query the underlying database.

### Install simple_db_api.sh as a service

If you need to make these changes permanent (i.e. have the **simple_db_api** web server start at boot), 
you can use the [etc/init.d/simple_db_api.sh](etc/init.d/simple_db_api.sh) **as a starting point**.
It is a script that can be read by systemd, but it has not been tested 

## Endpoint format

Select queries are done using GET requests and table names as full URL, e.g:

```
GET /users/ --> returns all the records of table 'users'
```

## Query string parameters

- **filter**: where clause, can be specified multiple times. It must be a string
  in the form `column_name:operator[:value]`, where **operator** can be:
    - eq: filters all the records where column_name is equal to **value**;
    - ne: filters all the records where column_name is equal to **value**;
    - gt: filters all the records where column_name is greater than **value**;
    - lt: filters all the records where column_name is less than **value**;
    - gte: filters all the records where column_name is greater than or equal to **value**;
    - lte: filters all the records where column_name is less than or equal to **value**;
    - null: filters all the records where column_name is **null** (value must not be specified);
    - not_null: filters all the records where column_name is **NOT null** (value must not be specified);
- **or**: boolean, default: False. If True and if there is more than one `filter`, they will be joined using **OR**
  (instead of the the default **AND**).
- **offset**: int, default: 0. Tells the API how many records to skip at the beginning of the recordset.
- **limit**: int, default: 20. Tells the API how many records to retrieve.
- **order**: string, optional. Name of the column to use for sorting. If we want a descendant sorting, prepend a '-' 
to the column name. E.g. to sort by 'age' in reverse order, use `order=-age` . 

  To sort by multiple columns, it's enough to repeat the `order` parameter, e.g.:
   
  `order=-age&order=first_name`

## Response

The API returns always a JSON object with the following attributes:

- **results**: array of the records returned by the query.
- **error**: optionally, the error message returned by the query.


## Supported database types

Only MySQL so far :(

## Dependencies reference

- [MySQL connector for Python](https://dev.mysql.com/doc/connector-python/en/connector-python-example-connecting.html)

---

(c) Paolo Stefan www.paolostefan.it