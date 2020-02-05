# Simple Python db API

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

## reference

https://dev.mysql.com/doc/connector-python/en/connector-python-example-connecting.html

(c) Paolo Stefan www.paolostefan.it