import pytest
import moto
from moto.ec2 import utils as ec2_utils
import boto3
import re
import json
from itertools import groupby


class TestAWSECSAmiUpdate(object):

    def check_ami_id_format(self, amiid):
        ami = str(amiid)
        """Check if AMI is in correct format or raise exception."""
        id_check = re.match(r'ami-\w{8,17}', ami, re.M | re.I)
        if id_check is None:
            # Normally we would raise an exception here.
            return None
        else:
            return ami

    @moto.mock_ec2
    def create_instances(self):
        client = boto3.client('ec2', region_name='eu-west-1')
        reservation = client.run_instances(ImageId='ami-1234abcd', MaxCount=1, MinCount=1)
        instance = reservation['Instances'][0]
        return instance

    @moto.mock_ec2
    def create_ami(self):
        client = boto3.client('ec2', region_name='eu-west-1')
        instance = self.create_instances()
        source_image_id = client.create_image(InstanceId=instance['InstanceId'], Name="test-ami")
        amiobj = client.describe_images(ImageIds=[source_image_id['ImageId']])
        return amiobj, source_image_id

    @moto.mock_ec2
    def test_get_ami(self):
        amiobj, srcimgid = self.create_ami()
        assert amiobj['Images'][0]['ImageId'] == srcimgid['ImageId']

    @moto.mock_ecs
    def create_ecs_cluster(self, clustername):
        client = boto3.client('ecs', region_name='eu-west-1')
        ecs_cluster = client.create_cluster(clusterName=clustername)
        return ecs_cluster

    @moto.mock_ecs
    def test_list_clusters(self):
        client = boto3.client('ecs', region_name='eu-west-1')
        create_resp = self.create_ecs_cluster(clustername="testcluster")
        list_resp = client.list_clusters()
        assert create_resp['cluster']['clusterArn'] in list_resp['clusterArns']

    @moto.mock_ec2
    @moto.mock_ecs
    def test_list_container_instances(self):
        ecs_client = boto3.client('ecs', region_name='eu-west-1')
        ec2 = boto3.resource('ec2', region_name='eu-west-1')

        test_cluster_name = 'test_ecs_cluster'
        _ = ecs_client.create_cluster(
            clusterName=test_cluster_name
        )

        instance_to_create = 3
        test_instance_arns = []
        amiobj, srcimgid = self.create_ami()
        for i in range(0, instance_to_create):
            test_instance = ec2.create_instances(
                ImageId=srcimgid['ImageId'],
                MinCount=1,
                MaxCount=1,
            )[0]

            instance_id_document = json.dumps(
                ec2_utils.generate_instance_identity_document(test_instance)
            )

            response = ecs_client.register_container_instance(
                cluster=test_cluster_name,
                instanceIdentityDocument=instance_id_document)

            test_instance_arns.append(response['containerInstance'][
                                          'containerInstanceArn'])

        response = ecs_client.list_container_instances(cluster=test_cluster_name)
        assert len(response['containerInstanceArns']) == instance_to_create
        for arn in test_instance_arns:
            assert arn in response['containerInstanceArns']

    @moto.mock_ec2
    @moto.mock_ecs
    def test_get_ecs_instance_id(self):
        ecs_client = boto3.client('ecs', region_name='eu-west-1')
        ec2 = boto3.resource('ec2', region_name='eu-west-1')

        test_cluster_name = 'test_ecs_cluster'
        _ = ecs_client.create_cluster(
            clusterName=test_cluster_name
        )

        instance_to_create = 3
        test_instance_arns = []
        test_instance_ids = []
        amiobj, srcimgid = self.create_ami()
        for i in range(0, instance_to_create):
            test_instance = ec2.create_instances(
                ImageId=srcimgid['ImageId'],
                MinCount=1,
                MaxCount=1,
            )[0]

            instance_id_document = json.dumps(
                ec2_utils.generate_instance_identity_document(test_instance)
            )

            response = ecs_client.register_container_instance(
                cluster=test_cluster_name,
                instanceIdentityDocument=instance_id_document)

            test_instance_arns.append(response['containerInstance'][
                                          'containerInstanceArn'])
            test_instance_ids.append(test_instance.id)
        response = ecs_client.describe_container_instances(
            cluster=test_cluster_name, containerInstances=test_instance_arns)
        assert len(response['failures']) == 0
        assert len(response['containerInstances']) == instance_to_create
        response_arns = [ci['containerInstanceArn']
                         for ci in response['containerInstances']]
        response_ids = [i['ec2InstanceId'] for i in response['containerInstances']]
        for arn in test_instance_arns:
            assert arn in response_arns
        for id in test_instance_ids:
            assert id in response_ids

    @moto.mock_ec2
    def test_get_ecs_instance_amiid(self):
        ec2 = boto3.resource('ec2', region_name='eu-west-1')
        ec2client = boto3.client('ec2', region_name='eu-west-1')
        instance_to_create = 3
        test_instance_ids = []
        amiobj, srcimgid = self.create_ami()
        for i in range(0, instance_to_create):
            test_instance = ec2.create_instances(
                ImageId=srcimgid['ImageId'],
                MinCount=1,
                MaxCount=1,
            )[0]
            test_instance_ids.append(test_instance.id)
        resp = ec2client.describe_instances(InstanceIds=test_instance_ids)['Reservations']
        instances = sum([[i for i in r['Instances']] for r in resp], [])
        sorted_amis = groupby([i['ImageId'] for i in instances])
        ami_sub_list = [ami[0] for ami in sorted_amis]
        assert ami_sub_list[0] == srcimgid['ImageId']
        assert len(ami_sub_list) == 1

    @moto.mock_autoscaling
    def test_get_asg_launch_conf(self):
        asclient = boto3.client('autoscaling', region_name='eu-west-1')
        lc_name = 'test-lc'
        asclient.create_launch_configuration(LaunchConfigurationName=lc_name)
        assert asclient.describe_launch_configurations(LaunchConfigurationNames=[lc_name])['LaunchConfigurations'][0]['LaunchConfigurationName'] == lc_name

    @moto.mock_autoscaling
    def test_get_asgs(self):
        client = boto3.client('autoscaling', region_name='eu-west-1')
        _ = client.create_launch_configuration(
            LaunchConfigurationName='test_launch_configuration'
        )
        _ = client.create_auto_scaling_group(
            AutoScalingGroupName='test_asg',
            LaunchConfigurationName='test_launch_configuration',
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            AvailabilityZones=['eu-west-1a']
        )
        response = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test_asg"]
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        assert response['AutoScalingGroups'][0][
            'AutoScalingGroupName'] == 'test_asg'

    @moto.mock_autoscaling
    def test_create_asg_launch_conf(self):
        asclient = boto3.client('autoscaling', region_name='eu-west-1')
        lc_name = 'test-lc'
        response = asclient.create_launch_configuration(LaunchConfigurationName=lc_name)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    @moto.mock_autoscaling
    def test_update_asg_launch_conf(self):
        asclient = boto3.client('autoscaling', region_name='eu-west-1')
        lc_name = 'test-lc'
        _ = asclient.create_launch_configuration(
            LaunchConfigurationName=lc_name
        )
        _ = asclient.create_auto_scaling_group(
            AutoScalingGroupName='test_asg',
            LaunchConfigurationName=lc_name,
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            AvailabilityZones=['eu-west-1a']
        )
        _ = asclient.create_launch_configuration(
            LaunchConfigurationName='new-lc'
        )
        response = asclient.update_auto_scaling_group(
            AutoScalingGroupName='test_asg',
            LaunchConfigurationName='new-lc'
        )
        describe_resp = asclient.describe_auto_scaling_groups(
            AutoScalingGroupNames=['test_asg']
        )
        assert describe_resp['AutoScalingGroups'][0]['LaunchConfigurationName'] == 'new-lc'
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    @moto.mock_autoscaling
    def test_create_asg(self):
        asclient = boto3.client('autoscaling', region_name='eu-west-1')
        lc_name = 'test-lc'
        _ = asclient.create_launch_configuration(
            LaunchConfigurationName=lc_name
        )
        response = asclient.create_auto_scaling_group(
            AutoScalingGroupName='test_asg',
            LaunchConfigurationName=lc_name,
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            AvailabilityZones=['eu-west-1a']
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    @moto.mock_autoscaling
    def test_delete_asg(self):
        asclient = boto3.client('autoscaling', region_name='eu-west-1')
        lc_name = 'test-lc'
        _ = asclient.create_launch_configuration(
            LaunchConfigurationName=lc_name
        )
        response = asclient.create_auto_scaling_group(
            AutoScalingGroupName='test_asg',
            LaunchConfigurationName=lc_name,
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5,
            AvailabilityZones=['eu-west-1a']
        )
        del_response = asclient.delete_auto_scaling_group(
            AutoScalingGroupName='test_asg',
            ForceDelete=True
        )
        describe_resp = asclient.describe_auto_scaling_groups(
            AutoScalingGroupNames=['test_asg']
        )
        assert del_response['ResponseMetadata']['HTTPStatusCode'] == 200
        assert len(describe_resp['AutoScalingGroups']) == 0

    @moto.mock_autoscaling
    def test_delete_launch_conf(self):
        asclient = boto3.client('autoscaling', region_name='eu-west-1')
        lc_name = 'test-lc'
        response = asclient.create_launch_configuration(
            LaunchConfigurationName=lc_name)
        del_response = asclient.delete_launch_configuration(
            LaunchConfigurationName=lc_name
        )
        describe_resp = asclient.describe_launch_configurations(
            LaunchConfigurationNames=[lc_name]
        )
        assert del_response['ResponseMetadata']['HTTPStatusCode'] == 200
        assert len(describe_resp['LaunchConfigurations']) == 0

    @moto.mock_ec2
    @moto.mock_ecs
    def test_drain_ecs_container_instances(self):
        ecs_client = boto3.client('ecs', region_name='eu-west-1')
        ec2 = boto3.resource('ec2', region_name='eu-west-1')

        test_cluster_name = 'test_ecs_cluster'
        _ = ecs_client.create_cluster(
            clusterName=test_cluster_name
        )

        instance_to_create = 3
        test_instance_arns = []
        amiobj, srcimgid = self.create_ami()
        for i in range(0, instance_to_create):
            test_instance = ec2.create_instances(
                ImageId=srcimgid['ImageId'],
                MinCount=1,
                MaxCount=1,
            )[0]

            instance_id_document = json.dumps(
                ec2_utils.generate_instance_identity_document(test_instance)
            )

            response = ecs_client.register_container_instance(
                cluster=test_cluster_name,
                instanceIdentityDocument=instance_id_document)

            test_instance_arns.append(response['containerInstance'][
                                          'containerInstanceArn'])
        test_instance_ids = list(map((lambda x: x.split('/')[1]), test_instance_arns))
        response = ecs_client.update_container_instances_state(cluster=test_cluster_name,
                                                               containerInstances=test_instance_ids,
                                                               status='DRAINING')
        response_statuses = [ci['status'] for ci in response['containerInstances']]
        for status in response_statuses:
            assert status == 'DRAINING'

    @pytest.mark.parametrize('amistr, expected', [
        ('ami-809f84e6', 'ami-809f84e6'),
        ('ami-786f9v', None),
        ('ami897966979', None),
        ('ami-xc89#"34', None),
        (1234, None)
        ])
    def test_check_ami_id_format(self, amistr, expected):
        assert self.check_ami_id_format(amistr) == expected
