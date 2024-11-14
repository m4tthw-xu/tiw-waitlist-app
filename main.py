import boto3
from datetime import datetime
import os
from dotenv import load_dotenv
from boto3.dynamodb.conditions import Key, Attr

load_dotenv()
os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY')
os.environ['AWS_DEFAULT_REGION'] = os.getenv('AWS_DEFAULT_REGION')

dynamo = boto3.resource('dynamodb')

# REQUIRED: eid, name, phone, requested_bb, time
waitlist_table = dynamo.Table('tiw_waitlist')

# REQUIRED: eid, name, bb, time
# OPTIONAL: phone
checkout_table = dynamo.Table('tiw_checkouts')

'''
Return Code Key:
001 -- unknown error code

002 -- user is already in the waitlist
003 -- user's phone number is invalid
004 -- user already has bambu checked out

011 -- user does not have bambu checked out

024 -- user is already on the waitlist
025 -- invalid phone #

201 -- unknown waitlist error code

102 -- user added to waitlist

9xx -- machine (xx) was successfully checked to user
8xx -- machine (xx) was successfully returned
7xx -- machine (xx) was NOT successfully checked out
6xx -- machine (xx) was NOT successfully returned
999 -- user was sucessfully added to waitlist
990 -- user not successfully added to waitlist
'''
waitlist_logs = dynamo.Table('tiw_waitlist_logs')
def find_next_log_id():
    # Initialize variables
    max_value = None

    # Scan the table with a projection expression for the integer column
    response = waitlist_logs.scan(
        ProjectionExpression="log_id"
    )

    # Find the maximum value in the initial response
    for item in response['Items']:
        if 'log_id' in item:
            value = int(item['log_id'])  # Convert Decimal to int
            if max_value is None or value > max_value:
                max_value = value

    # Handle pagination if necessary
    while 'LastEvaluatedKey' in response:
        response = waitlist_logs.scan(
            ProjectionExpression="log_id",
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        for item in response['Items']:
            if 'log_id' in item:
                value = int(item['log_id'])
                if max_value is None or value > max_value:
                    max_value = value
    return max_value
def add_log(entry, code, message=''):
    log_id = find_next_log_id() + 1
    if entry is None:
        waitlist_logs.put_item(Item={
            'log_id': log_id,
            'code': code,
            'message': message,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
    else:
        waitlist_logs.put_item(Item={
            'log_id': log_id,
            'eid': entry['eid'],
            'name': entry['name'],
            'code': code,
            'message': message,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
def search_col(table, col_name, target):
    response = table.scan(
        FilterExpression=Attr(col_name).eq(target)
    )
    return response['Count'] > 0
def check_available(bb):
    response = checkout_table.scan(ProjectionExpression='bb')
    checked_out = []
    for i in response['Items']:
        if 'bb' in i:
            checked_out.append(i['bb'])
    checked_out = [int(num) for num in checked_out]
    if len(checked_out) == 18:
        return False

    if bb in checked_out:
        return False

    return True

def add_to_checkout(entry):
    eid = entry['eid']
    bb_num = entry['bb']

    if search_col(checkout_table, 'eid', eid):
        add_log(entry, '004', f"USER {eid} ALREADY EXISTS IN CHECKOUT")
        return '004'

    if not check_available(bb_num):
        code = "{:02}".format(bb_num)
        add_log(entry, f'7{code}', 'BAMBU IS NOT AVAILABLE')
        return f'7{code}'

    try: # check out the bb to the user
        checkout_table.put_item(Item=entry)
        code = "{:02}".format(bb_num)
        add_log(entry, f'9{code}', f'BAMBU {code} SUCCESSFULLY CHECKED OUT')
        return f'9{code}'
    except Exception as e:
        print(e)
        add_log(entry, '001', "UNKNOWN CHECKOUT ERROR")
        return '001'
def return_checkout(bb_num):
    if check_available(bb_num):
        code = "{:02}".format(bb_num)
        add_log(None, f'6{code}', 'BAMBU IS NOT CHECKED OUT')
        return f'6{code}'

    try: # return the bb from the user
        code = "{:02}".format(bb_num)
        checkout_table.delete_item(Key={'bb': bb_num})
        add_log(None, f'7{code}', f'BAMBU {code} SUCCESSFULLY CHECKED IN')
        return f'7{code}'
    except Exception as e:
        print(e)
        add_log(None, '001', "UNKNOWN CHECKOUT ERROR")
        return '001'

def add_to_waitlist(entry):
    eid = entry['eid']

    requested_bb = entry['requested_bb']
    # bb_num = entry['bb']

    if search_col(checkout_table, 'eid', eid):
        add_log(entry, '004', f"USER {eid} ALREADY EXISTS IN CHECKOUT")
        return '004'

    if search_col(waitlist_table, 'eid', eid):
        add_log(entry, '024', f"USER {eid} ALREADY EXISTS ON WAITLIST")
        return '024'

    # if any of the requested bbs are available
    for bb_num in entry['requested_bb']:
        if check_available(bb_num):
            code = "{:02}".format(bb_num)
            add_log(entry, f'6{code}', 'BAMBU IS AVAILABLE')
            return f'6{code}'

    # no bambu is not available AND user is not already in checkout or waitlist tables
    phone = entry['phone']  # this is to make sure that the phone number is entered
    if len(phone) != 10:
        add_log(entry, f'025', "INVALID PHONE NUMBER")
        return f'025'

    try:
        waitlist_table.put_item(Item=entry)
        add_log(entry, '999', f"USER {eid} ADDED TO THE WAITLIST")
        return '999'
    except Exception as e:
        print(e)
        add_log(entry, '201', "UNKNOWN WAITLIST ERROR")
        return '201'

# TODO: waitlist updating routine with sms messaging -- test sms before achieving this

if __name__ == '__main__':
    # simulate all checkouts
    # for i in range(1, 19):
    #     print(add_to_checkout({
    #         'bb': i,
    #         'eid': f't00{i}',
    #         'name': f'Test {i}',
    #         'time': datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    #     }))

    # print(add_to_checkout({
    #     'eid': 't123',
    #     'name': 'Test Matt',
    #     'bb': 1,
    #     'time': datetime.now().strftime('%m/%d/%Y %H:%M:%S')
    # }))

    # for i in range(2, 13, 3):
    #     print(return_checkout(i))

    # print(return_checkout(4))

    # print(add_to_waitlist({
    #     'eid': 't0018',
    #     'name': "Test me",
    #     'requested_bb': {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}, # any bb
    #     'phone': '71382450',
    #     'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    # }))

    print(add_to_waitlist({
        'eid': 't1234',
        'name': "Test me",
        'requested_bb': {15, 16},  # any bb
        'phone': '7138242450',
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }))

