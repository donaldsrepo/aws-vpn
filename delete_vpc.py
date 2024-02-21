"""
WARNING!!
    This script deletes the VPC and all the dependencies
    associated with it. This should be complete. It has the same effect as 
    selecting Delete from the menu on a VPC in the AWS Console and also
    deletes internet gateways that are attached to the VPC.

    1.) Delete the internet-gateway
    2.) Delete subnets
    3.) Delete route-tables
    4.) Delete network access-lists
    5.) Delete security-groups
    6.) Delete the VPC 
    7.) Does not delete the related Subnet Groups (we may be using those somewhere else)

TO RUN:

    python [-m pdb] delete_vpc.py vpc-01d06fc4171d0bd0e

"""

import sys
import boto3


def vpc_cleanup(vpc_id):
    """Remove VPC from AWS
    Set your region/access-key/secret-key from env variables or boto config.
    :param vpc_id: id of vpc to delete
    """
    delete_flag = True
    if not vpc_id:
        return
    if delete_flag == True:
        print('Removing VPC ({}) from AWS'.format(vpc_id))
    else:
        print(f'Displaying dependencies for VPC ({vpc_id}) from AWS')
    ec2 = boto3.resource('ec2', region_name='us-west-2')
    ec2client = ec2.meta.client
    vpc = ec2.Vpc(vpc_id)
    # detach and delete all gateways associated with the vpc
    for gw in vpc.internet_gateways.all():
        if delete_flag == True:
            vpc.detach_internet_gateway(InternetGatewayId=gw.id)
            gw.delete()
        else:
            print(f"gateway: {gw.id}")
    # delete all route table associations
    for rt in vpc.route_tables.all():
        print(f"route_table: {rt}")
        for rta in rt.associations:
            if not rta.main:
                if delete_flag == True:
                    rta.delete()
                else:
                    print(f"  route_table association: {rta}")
    # delete any subnet instances
    for subnet in vpc.subnets.all():
        for instance in subnet.instances.all():
            if delete_flag == True:
                instance.terminate()
            else:
                print(f"subnet: {instance}")
    # delete our endpoints
    for ep in ec2client.describe_vpc_endpoints(
            Filters=[{
                'Name': 'vpc-id',
                'Values': [vpc_id]
            }])['VpcEndpoints']:
        if delete_flag == True:
            ec2client.delete_vpc_endpoints(VpcEndpointIds=[ep['VpcEndpointId']])
        else:
            print(f"vpc endpoint: {ep}")
    # delete our security groups
    for sg in vpc.security_groups.all():
        if sg.group_name != 'default':
            if delete_flag == True:
                sg.delete()
            else:
                print(f"security group: {sg}")
        else:
            print(f"default security group - not deleting: {sg}")
    # delete any vpc peering connections
    for vpcpeer in ec2client.describe_vpc_peering_connections(
            Filters=[{
                'Name': 'requester-vpc-info.vpc-id',
                'Values': [vpc_id]
            }])['VpcPeeringConnections']:
        if delete_flag == True:
            ec2.VpcPeeringConnection(vpcpeer['VpcPeeringConnectionId']).delete()
        else:
            print(f"vpc peer: {vpcpeer}")
    # delete non-default network acls
    for netacl in vpc.network_acls.all():
        if not netacl.is_default:
            if delete_flag == True:
                netacl.delete()
            else:
                print(f"network acl: {netacl}")
        else:
            print(f"default network acl - not deleting: {netacl}")
    # delete network interfaces
    for subnet in vpc.subnets.all():
        for interface in subnet.network_interfaces.all():
            if delete_flag == True:
                interface.delete()
            else:
                print(f"network interface: {interface}")
        if delete_flag == True:
            subnet.delete()
        else:
            print(f"subnet: {subnet}")
    # finally, delete the vpc
    if delete_flag == True:
        ec2client.delete_vpc(VpcId=vpc_id)
    else:
        print(f"vpc: {ec2client}")


def main(argv=None):
    vpc_cleanup(argv[1])


if __name__ == '__main__':
    main(sys.argv)