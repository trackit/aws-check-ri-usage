import boto3
import botocore
import json
from datetime import datetime, date, timedelta
import csv

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


def get_regions(session):
    client = session.client('ec2')
    regions = client.describe_regions()
    return [
        region['RegionName']
        for region in regions['Regions']
    ]

def get_reservations(account, session, regions):
    res = []
    for region in regions:
        client = session.client('ec2', region_name=region)
        for reserved_instance in client.describe_reserved_instances(
                Filters=[{'Name': 'state', 'Values': ['active']}])['ReservedInstances']:
            res += [
                {
                    'Account': account,
                    'region': region,
                    'OfferingType': reserved_instance['OfferingType'],
                    'InstanceType': reserved_instance['InstanceType'],
                    'InstanceCount': reserved_instance['InstanceCount'],
                    'End': reserved_instance['End'],
                    'Unused': 0
                }
            ]
    return res

def get_instances(account, session, regions):
    res = []
    for region in regions:
        client = session.client('ec2', region_name=region)
        reservations = client.describe_instances()
        res += [
            {
                'account': account,
                'type': instance['InstanceType'],
                'region': region,
                'used': 0
            }
            for reservation in reservations['Reservations']
            for instance in reservation['Instances']
        ]
    return res

def check_used_ri(instances, reservations):
    for reservation in reservations:
        to_use = reservation['InstanceCount']
        for instance in instances:
            if instance['region'] == reservation['region'] and instance['used'] == 0 and instance['type'] == reservation['InstanceType']:
                instance['used'] = 1
                to_use -= 1
                if to_use == 0:
                    break
        reservation['Unused'] = to_use
    return reservations

def generate_csv(data, header_name):
    with open('report.csv', 'wb') as file:
        writer = csv.DictWriter(file, header_name)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

KEYS = [
    {
        'name': '',
        'key': '',
        'secret': '',
    },
]


def main():
    data = []
    instances = []
    reservations = []
    for key in KEYS:
        print 'Processing %s...' % key['name']
        try:
            session = boto3.Session(aws_access_key_id=key['key'], aws_secret_access_key=key['secret'], region_name="us-east-1")
            regions = get_regions(session)
            instances += get_instances(key['name'], session, regions)
            reservations += get_reservations(key['name'], session, regions)
        except botocore.exceptions.ClientError, error:
            print error
    result = check_used_ri(instances, reservations)
    generate_csv(result, ['Account', 'region', 'OfferingType', 'InstanceType', 'InstanceCount', 'End', 'Unused'])
    print json.dumps(result, indent=4, default=json_serial)

if __name__ == '__main__':
    main()
