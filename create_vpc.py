#!/usr/bin/env python
# coding: utf-8
"""
conda create --name aws-cloud python=3.9 -c conda-forge
conda install -c conda-forge psycopg2 boto3
"""
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timezone

# RDS Clients
session = boto3.Session()
rds_client = session.client('rds', region_name='us-west-2')

# EC2 Clients
ec2_client = boto3.client('ec2', region_name="us-west-2")
ec2 = boto3.resource('ec2', region_name='us-west-2')

vpc = ec2.create_vpc(
    CidrBlock='172.32.0.0/16',
    DryRun=False,
    InstanceTenancy='default'
)

# Assign tags to the VPC and get id when finished
vpc.create_tags(Tags=[{"Key": "Name", "Value": "my_vpc"}])
vpc.wait_until_available()
print(vpc.id)

# Create and Attach the Internet Gateway
ig = ec2.create_internet_gateway()
vpc.attach_internet_gateway(InternetGatewayId=ig.id)
print(ig.id)

# Create Subnets
subnet1 = ec2.create_subnet(
    CidrBlock='172.32.16.0/20', 
    DryRun=False,
    VpcId=vpc.id,
    AvailabilityZone='us-west-2a'
)
print(subnet1.id)
subnet2 = ec2.create_subnet(
    CidrBlock='172.32.32.0/20', 
    DryRun=False,
    VpcId=vpc.id,
    AvailabilityZone='us-west-2b'
)
print(subnet2.id)
subnet3 = ec2.create_subnet(
    CidrBlock='172.32.0.0/20', 
    DryRun=False,
    VpcId=vpc.id,
    AvailabilityZone='us-west-2c'
)
print(subnet3.id)
subnet4 = ec2.create_subnet(
    CidrBlock='172.32.48.0/20', 
    DryRun=False,
    VpcId=vpc.id,
    AvailabilityZone='us-west-2d'
)
print(subnet4.id)

sn_all = ec2_client.describe_subnets()
for sn in sn_all['Subnets']:
    print(f"subnet id: {sn['SubnetId']}")
    print(f"subnet {sn}")

# todo: associate gateway with route table
route_tables = ec2_client.describe_route_tables( 
    DryRun=False, 
    Filters=[{'Name': 'vpc-id', 'Values': [vpc.id]},] 
)
route_id = route_tables['RouteTables'][0]['Associations'][0]['RouteTableId']
response = ec2_client.create_route(
    DryRun=False, 
    GatewayId=ig.id, 
    RouteTableId=route_id, 
    DestinationCidrBlock="0.0.0.0/0"
)

# enable public dns hostname
ec2_client.modify_vpc_attribute(
    VpcId = vpc.id, 
    EnableDnsSupport = {"Value": True}
)
ec2_client.modify_vpc_attribute(
    VpcId = vpc.id, 
    EnableDnsHostnames = {"Value": True}
)

# setup Auto-Assign public IPv4 address
ec2_client.modify_subnet_attribute(
    SubnetId=subnet1.id, 
    MapPublicIpOnLaunch={'Value': True}
)
ec2_client.modify_subnet_attribute(
    SubnetId=subnet2.id, 
    MapPublicIpOnLaunch={'Value': True}
)
ec2_client.modify_subnet_attribute(
    SubnetId=subnet3.id, 
    MapPublicIpOnLaunch={'Value': True}
)
ec2_client.modify_subnet_attribute(
    SubnetId=subnet4.id, 
    MapPublicIpOnLaunch={'Value': True}
)

subnet_group = "test-api-subnet-group"
subnet_groups = rds_client.describe_db_subnet_groups(
    DBSubnetGroupName=subnet_group,
    # find any subnet groups that are associated with our VPC
    # Filters=[{'Name': 'VpcId', 'Values': [vpc.id]},] 
)

create_subnet_group_flag = True
for subnet_group_names in subnet_groups['DBSubnetGroups']:
    print(subnet_group_names['DBSubnetGroupName'])
    print(subnet_group_names['VpcId'])
    if subnet_group_names['DBSubnetGroupName'] == subnet_group:
        create_subnet_group_flag = False
        print("Subnet Group already exists, cannot create! Either delete this first, or use with the current settings")

if create_subnet_group_flag == True:
    response = rds_client.create_db_subnet_group(
        DBSubnetGroupName=subnet_group,
        DBSubnetGroupDescription='test-api-subnet-group-desc',
        SubnetIds = [subnet1.id,subnet2.id,subnet3.id,subnet4.id]
    )
else:
    print("Not creating Subnet Group!!")

sg = ec2_client.create_security_group(
    GroupName='app-vpc-api-dev', 
    Description = 'Created by Python Script', 
    VpcId=vpc.id
)
security_group_id = sg.get('GroupId')
print(security_group_id)

# add inbound rule to security group for external access (PGAdmin) and this script to connect
#     Settings: IPv4, PostgreSQL, TCP, 5432, Source Anywhere-IPv4: 0.0.0.0/0
port_range_start = 5432
port_range_end = 5432
protocol = 'TCP'
# ip addresses for your laptop/pc
cidr1 = "170.120.130.10/32"
cidr2 = "160.210.130.4/32"
# public access to VPC
cidr3 = "0.0.0.0/0"
description = 'Needed for Aurora Postgres access from laptop'
ec2 = boto3.resource('ec2', region_name='us-west-2')
security_group = ec2.SecurityGroup(security_group_id)
response = security_group.authorize_ingress(
    DryRun=False,
    IpPermissions=[
        {
            'FromPort': port_range_start,
            'ToPort' : port_range_end,
            'IpProtocol': protocol,
            'IpRanges': [
                {
                    'CidrIp': cidr1, 
                    'Description': description
                },
            ]
        }
    ]
)
print(response)
response = security_group.authorize_ingress(
    DryRun=False,
    IpPermissions=[
        {
            'FromPort': port_range_start,
            'ToPort' : port_range_end,
            'IpProtocol': protocol,
            'IpRanges': [
                {
                    'CidrIp': cidr2, 
                    'Description': description
                },
            ]
        }
    ]
)
print(response)
response = security_group.authorize_ingress(
    DryRun=False,
    IpPermissions=[
        {
            'FromPort': port_range_start,
            'ToPort' : port_range_end,
            'IpProtocol': protocol,
            'IpRanges': [
                {
                    'CidrIp': cidr3, 
                    'Description': 'Access from Internet'
                },
            ]
        }
    ]
)
print(response)
