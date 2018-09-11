import boto3
import os

dynamodb = boto3.resource('dynamodb',
                           aws_access_key_id=os.environ["AWS_ACCESS"],
                           aws_secret_access_key=os.environ["AWS_SECRET"])
dota_table = dynamodb.Table(os.environ["DOTA_MATCH_TABLE"])