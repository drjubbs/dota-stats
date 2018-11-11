import boto3
import os

class AWS:    
    def __init__(self, table_name):
        self.dynamodb = boto3.resource('dynamodb',
                                   aws_access_key_id=os.environ["AWS_ACCESS"],
                                   aws_secret_access_key=os.environ["AWS_SECRET"],
                                   region_name='us-east-2')
        self.dota_table = self.dynamodb.Table(table_name)
             