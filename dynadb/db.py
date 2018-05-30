import pandas as pd
import MySQLdb, time 
from sqlalchemy import create_engine
import  sqlalchemy.exc
import memcache
from sqlalchemy import MetaData
from sqlalchemy import Table
import pandas.io.sql as psql

mc = memcache.Client(['127.0.0.1:11211'],debug=0)


#c = cfg.config()

# class DbInstance:
       
#   def __init__(self, host):
#     """
#     - The constructor for database instance.

#     :param host: Instance hostname.
#     :type host: str
    

#     Example Output::

#         >>> x = DbInstance('local')
#         >>> x.name, x.host, x.user, x.password
#         ('senslopedb', '127.0.0.1', 'root', 'admin')


#     """      
#     sc = mc.get('server_config')
#     self.name = sc['db']['name'] 
#     self.host = sc['hosts'][host] 
#     self.user = sc['db']['user'] 
#     self.password = sc['db']['password']
      
      
def get_connection_dict(connection):
    dbc = mc.get('DICT_DB_CONNECTIONS')
    dbc = dbc[connection]
    return dbc


def get_resouce_dict(resource):
    resources_dict = mc.get('DICT_DB_RESOURCES')

    resources_section = resources_dict.keys()

    resource_list_exists = []
    print resource
    for section in resources_section:
       resource_list = resources_dict[section]['resources']
       if resource in resource_list:
            resource_list_exists.append(section)
    if len(resource_list_exists) == 1:
         print resource_list_exists[0] 
         return resource_list_exists[0]  
    elif len(resource_list_exists) > 1:
        print ">> List of connection for this resource"
        print resource_list_exists
        return
    else:
        print ">> Unknown resource"
        return


def connect(host = '', connection = '', resource = '' , set_host ='',
    set_user = '',set_password = '',set_schema = '', set_port = '', 
    conn_type = 'connect'):   
    """
    - Creating the ``MySQLdb.connect`` and ``create_engine``connetion for the database.

    Args:
        host (str): Hostname.

    Returns:
        Returns the ``MySQLdb.connect()`` as db and ``db.cursor()`` as cur 
        connection to the host.

    Raises:
        MySQLdb.OperationalError: Error in database connection.

    """ 
    #dbc = database connection

    if connection:
        dbc = get_connection_dict(connection)
    elif resource:
        connection_name = get_resouce_dict(resource)
        if connection_name:
            dbc = get_connection_dict(connection_name)
            db_connect = True
        else:
            db_connect = False
    else:
        dbc = dict()
        sc = mc.get('server_config')
        dbc['host'] = sc['hosts'][host] 
        dbc['user'] = sc['db']['user'] 
        dbc['password'] = sc['db']['password']
        dbc['schema'] = sc['db']['name'] 
        db_connect = True

    while db_connect:
        if set_host:
            dbc['host'] = set_host
        elif set_user:
            dbc['user'] = set_user
        elif set_password:
            dbc['password'] = set_password
        elif set_schema:
            dbc['schema'] = set_schema 

        if conn_type == 'connect':
            try:
                db = MySQLdb.connect(dbc['host'], dbc['user'], 
                    dbc['password'], dbc['schema'])
                cur = db.cursor()
                return db, cur
            except MySQLdb.OperationalError:
            # except IndexError:
                print '6.',
                time.sleep(2)
        elif engine_type == 'create_engine' :
            try:
                engine = create_engine('mysql+pymysql://' + 
                    dbc['user'] + ':'+ dbc['password'] + '@' + 
                    dbc['host'] +':3306/' + dbc['schema'])
                return engine
            except sqlalchemy.exc.OperationalError:
                print ">> Error connetion"



def write(query = '', identifier = '', last_insert = False, 
    instance = 'local' , connection = '' , resource = '' , set_host ='',
    set_user = '',set_password = '' ,set_schema = '', set_port = ''):
    """
    - The process of writing to the database by a query statement.

    Args:
        query (str): Query statement.
        identifier (str): Identifier statement for the query.
        Last_insert (str): Select the last insert. Defaults to False.
        instance (str): Hostname. Defaults to local.
    
    Raises:
        IndexError: Error in retry index.
        KeyError: Error on writing to database.
        MySQLdb.IntegrityError: If duplicate entry detected.

    """ 
    db, cur = connect(instance, connection, resource, set_host,
        set_user, set_password, set_schema, set_port)

    b=''
    try:
        retry = 0
        while True:
            try:
                a = cur.execute(query)

                b = ''
                if last_insert:
                    b = cur.execute('select last_insert_id()')
                    b = cur.fetchall()

                if a:
                    db.commit()
                    break
                else:

                    db.commit()
                    time.sleep(0.1)
                    break

            except IndexError:
                print '5.',

                if retry > 10:
                    break
                else:
                    retry += 1
                    time.sleep(2)
    except KeyError:
        print '>> Error: Writing to database', identifier
    except MySQLdb.IntegrityError:
        print '>> Warning: Duplicate entry detected', identifier
    db.close()
    return b


def read(query = '', identifier = '', instance = 'local', 
    connection = '' , resource = '' , set_host ='', set_user = '', 
    set_password = '' ,set_schema = '', set_port = ''):
    """
    - The process of reading the output from the query statement.

    Args:
        query (str): Query statement.
        identifier (str): Identifier statement for the query.
        instance (str): Hostname. Defaults to local.

    Returns:
      tuple: Returns the query output and fetch by a ``cur.fetchall()``.

    Raises:
        KeyError: Key interruption.
        MySQLdb.OperationalError: Error in database connection.
        ValueError: Error in execution of the query.

    Example Output::
            
        >> print read(query='SELECT * FROM senslopedb.loggers limit 3', identifier='select loggers')
        ((1, 1, 'agbsb', datetime.date(2015, 8, 31), None, Decimal('11.280820'), Decimal('122.831300'), 3), 
        (2, 1, 'agbta', datetime.date(2015, 8, 31), None, Decimal('11.281370'), Decimal('122.831100'), 6), 
        (3, 2, 'bakg', datetime.date(2016, 8, 9), None, Decimal('16.789631'), Decimal('120.660903'), 31))

    """ 

    db, cur = connect(instance, connection, resource, set_host,
        set_user, set_password, set_schema, set_port)

    a = ''
    
    try:
        a = cur.execute(query)
        a = None
        try:
            a = cur.fetchall()
            return a
        except ValueError:
            return None
    except MySQLdb.OperationalError:
        a =  None
    except KeyError:
        a = None


# def df_engine(host = 'local', connection = '' , resource = '', set_host ='',
#     set_user = '',set_password = '' ,set_schema = '', set_port = ''):
#     """
#     - Creating the engine connection for the database.

#     Args:
#         host (str): Hostname. Defaults to local.

#     Returns:
#         Returns the ``create_engine()`` connection to the host.


#     """ 
#     if connection != "":
#         dbc = get_connection_dict(connection)
#         host = dbc['host']
#         passwd = dbc['password']
#         user = dbc['user']
#         db = dbc['schema']

#     elif resource != "":
#         connection = get_resouce_dict(resource)
#         dbc = get_connection_dict(connection)
#         host = dbc['host']
#         passwd = dbc['password']
#         user = dbc['user']
#         db = dbc['schema']
#     else:
#         dbc = DbInstance(host)
#         host = dbc.host,
#         user = dbc.user, 
#         passwd = dbc.password, 
#         db = dbc.name
    

#     engine = create_engine('mysql+pymysql://' + user + ':'
#         + password + '@' + host + ':3306/' + name)
#     # return engine


def df_write(data_table, host = 'local', last_insert = False , 
    connection = '' , resource = '', set_host ='', set_user = '', 
    set_password = '' ,set_schema = '', set_port = ''):
    """
    - The process of writing data frame data to a database.

    Args:
        data_table (obj): DataTable class object from smsclass.py.
        host (str): Hostname. Defaults to local.

    Raises:
        IndexError: Possible data type error.
        ValueError: Value error detected.
        AttributeError: Value error in data pass.


    """
    engine = connect(host, connection, resource, set_host,
        set_user, set_password, set_schema, set_port, 
        conn_type='create_engine')

    df = data_table.data
    df = df.drop_duplicates(subset = None, keep = 'first', inplace = False)
    value_list = str(df.values.tolist())[:-1][1:]
    value_list = value_list.replace("]",")").replace("[","(")
    column_name_str = str(list(df))[:-1][1:].replace("\'","")
    duplicate_value_str = ", ".join(["%s = VALUES(%s)" % (name, name) 
        for name in list(df)]) 
    query = "insert into %s (%s) values %s" % (data_table.name,
        column_name_str, value_list)
    query += " on DUPLICATE key update  %s " % (duplicate_value_str)
    try:
        last_insert_id = write(query = query, 
            identifier = 'Insert dataFrame values', 
            last_insert = last_insert,
            instance = host)
        return last_insert_id
    except IndexError:
        print "\n\n>> Error: Possible data type error"
    except ValueError:
        print ">> Value error detected"   
    except AttributeError:
        print ">> Value error in data pass"       


def df_read(query = '', host = 'local', connection = '', resource = '', set_host ='',
    set_user = '', set_password = '' ,set_schema = '', set_port = '', 
    conn_type='create_engine'):

    db, cur = connect(host, connection, resource, set_host,
        set_user, set_password, set_schema, set_port,conn_type)
    ret_val = None
    try:
        df = psql.read_sql(query, db)
        ret_val = df
    except KeyboardInterrupt:
        print "Exception detected in accessing database"
        sys.exit()
    except psql.DatabaseError:
        print "Error getting query %s" % (query)
        ret_val = None
    finally:
        return ret_val


