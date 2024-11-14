import os
import boto3

from dotenv import load_dotenv

load_dotenv()

os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')
os.environ['AWS_DEFAULT_REGION'] = os.getenv('AWS_DEFAULT_REGION')

dynamo = boto3.resource('dynamodb')

def create_tiw_waitlist():
    table = dynamo.create_table(
        TableName='tiw_waitlist',

        KeySchema=[
            {
                'AttributeName': 'eid',
                'KeyType': 'HASH'
            }
        ],

        AttributeDefinitions = [
            {
                'AttributeName': 'eid',
                'AttributeType': 'S'
            }

        ],

        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

def create_tiw_checkouts():
    table = dynamo.create_table(
        TableName='tiw_checkouts',

        KeySchema=[
            {
                'AttributeName': 'bb',
                'KeyType': 'HASH',
            }
        ],

        AttributeDefinitions = [
            {
                'AttributeName': 'bb',
                'AttributeType': 'N'
            }
        ],

        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )

'''
Error Code Key:
000 -- unknown error code
001 -- user is already in the waitlist
002 -- user's phone number is invalid
9xx -- machine (xx) was successfully checked to user
8xx -- machine (xx) was successfully returned
'''
def create_tiw_logs():
    table = dynamo.create_table(
        TableName='tiw_waitlist_logs',

        KeySchema=[
            {
                'AttributeName': 'log_id',
                'KeyType': 'HASH'
            }
        ],

        AttributeDefinitions = [
            {
                'AttributeName': 'log_id',
                'AttributeType': 'N'
            }
        ],

        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )


create_tiw_waitlist()

