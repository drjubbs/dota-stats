"""
Delete current tables and re-create
"""
import aws
import os

try:
    aws.dota_table.delete()
except:
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
 
table = aws.dynamodb.create_table(
    TableName=aws.os.environ["DOTA_MATCH_TABLE"],
    
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
        'ReadCapacityUnits': 25,
        'WriteCapacityUnits': 25
    })

# Wait until the table exists.
table.meta.client.get_waiter('table_exists').wait(TableName=aws.os.environ["DOTA_MATCH_TABLE"])

# Print out some data about the table.
print(table.item_count)
