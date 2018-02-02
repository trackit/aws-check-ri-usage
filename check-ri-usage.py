import boto3
import botocore
import json
from datetime import datetime, date, timedelta
import csv
import ConfigParser
import os
import argparse

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

def generate_csv(data, args, header_name):
    filename = "report.csv"
    if args['o']:
        filename = args['o']
    with open(filename, 'wb') as file:
        writer = csv.DictWriter(file, header_name)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

def init():
    config_path = os.environ.get('HOME') + "/.aws/credentials"
    parser = ConfigParser.ConfigParser()
    parser.read(config_path)
    if parser.sections():
        return parser.sections()
    return []

def main():
    instances = []
    reservations = []
    parser = argparse.ArgumentParser(description="Analyse reserved instances")
    parser.add_argument("--profile", nargs="+", help="Specify AWS profile(s) (stored in ~/.aws/credentials) for the program to use")
    parser.add_argument("-o", nargs="?", help="Specify output csv file")
    parser.add_argument("--profiles-all", nargs="?", help="Run it on all profile")
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    aws_region = os.environ.get('AWS_DEFAULT_REGION')
    args = vars(parser.parse_args())
    if 'profiles-all' in args:
        keys = init()
    elif 'profile' in args and args['profile']:
        keys = args['profile']
    else:
        keys = init()
    for key in keys:
        print 'Processing %s...' % key
        try:
            if aws_access_key and aws_secret_key and aws_region:
                session = boto3.Session(aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name=aws_region)
            else:
                session = boto3.Session(profile_name=key)
            regions = get_regions(session)
            instances += get_instances(key, session, regions)
            reservations += get_reservations(key, session, regions)
        except botocore.exceptions.ClientError, error:
            print error
    result = check_used_ri(instances, reservations)
    generate_csv(result, args, ['Account', 'region', 'OfferingType', 'InstanceType', 'InstanceCount', 'End', 'Unused'])
    print json.dumps(result, indent=4, default=json_serial)

if __name__ == '__main__':
    main()
