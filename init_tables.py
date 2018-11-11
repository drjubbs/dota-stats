"""Initialize Maria DB and DynamoDb tables. 
"""
import aws
import os
import sys
import mysql.connector as mariadb
import logging

# Setup logging
log=logging.getLogger("dota")
log.setLevel(logging.DEBUG)
ch=logging.StreamHandler(sys.stdout)
fmt=logging.Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                datefmt="%Y-%m-%dT%H:%M:%S %Z")
ch.setFormatter(fmt)
log.addHandler(ch)

def usage():
    print("Usage: python init_tables.py <table name> <capacity>\n")
    print("Note: Ensure capacity stays within free tier or charges will apply.")
    quit()

if len(sys.argv)<3:
    usage()    
else:
    try:
        table_name = sys.argv[1]
        capacity = int(sys.argv[2])
    except:
        usage()

# Try and delete table if it exists
this_aws=aws.AWS(table_name)
try:    
    this_aws.dota_table.delete()
    print("Deleting table: {0}".format(table_name))
except:
    print("Did not match table: {0}".format(table_name))
    pass
    
attribute_dict = {
    'batch_time' : 'N', 
    'match_id' : 'N'
}

attribute_list = []
for k,v in attribute_dict.items():
    attribute_list.append(
        {
            'AttributeName' : k,
            'AttributeType' : v 
        })
 
table = this_aws.dynamodb.create_table(
    TableName=table_name,
    
    KeySchema = [
        {
            'AttributeName' : 'batch_time',
            'KeyType' : 'HASH'

        },
        {
            'AttributeName' : 'match_id',
            'KeyType' : 'RANGE'

        }
    ],
    AttributeDefinitions=attribute_list,
    ProvisionedThroughput={
        'ReadCapacityUnits': capacity,
        'WriteCapacityUnits': capacity
    })

# Wait until the table exists.
table.meta.client.get_waiter('table_exists').wait(TableName=table_name)

# Print out some data about the table.
print(table.item_count)
