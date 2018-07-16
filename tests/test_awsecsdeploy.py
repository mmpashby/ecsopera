import pytest
import moto
from moto.ec2 import utils as ec2_utils
import boto3
import re
import json
from itertools import groupby


class TestAWSECSDeploy(object):

    @moto.mock_ec2
    def create_ami(self):
        client = boto3.client('ec2', region_name='eu-west-1')
        instance = self.create_instances()
        source_image_id = client.create_image(InstanceId=instance['InstanceId'], Name="test-ami")
        amiobj = client.describe_images(ImageIds=[source_image_id['ImageId']])
        return amiobj, source_image_id

    @moto.mock_ec2
    def create_instances(self):
        client = boto3.client('ec2', region_name='eu-west-1')
        reservation = client.run_instances(ImageId='ami-1234abcd', MaxCount=1, MinCount=1)
        instance = reservation['Instances'][0]
        return instance

    @moto.mock_ecs
    def test_get_service_task_arn(self):
        client = boto3.client('ecs', region_name='eu-west-1')
        _ = client.create_cluster(
            clusterName='test_ecs_cluster'
        )
        _ = client.register_task_definition(
            family='test_ecs_task',
            containerDefinitions=[
                {
                    'name': 'hello_world',
                    'image': 'docker/hello-world:latest',
                    'cpu': 1024,
                    'memory': 400,
                    'essential': True,
                    'environment': [{
                        'name': 'AWS_ACCESS_KEY_ID',
                        'value': 'SOME_ACCESS_KEY'
                    }],
                    'logConfiguration': {'logDriver': 'json-file'}
                }
            ]
        )
        _ = client.create_service(
            cluster='test_ecs_cluster',
            serviceName='test_ecs_service1',
            taskDefinition='test_ecs_task',
            desiredCount=2
        )
        response = client.describe_services(
            cluster='test_ecs_cluster',
            services=['test_ecs_service1']
        )
        task_response = client.describe_task_definition(
            taskDefinition='test_ecs_task'
        )
        assert len(response['services']) == 1
        assert response['services'][0]['serviceName'] == 'test_ecs_service1'
        assert task_response['taskDefinition']['taskDefinitionArn'] == response['services'][0]['taskDefinition']

    @moto.mock_ecs
    def test_get_service_task_obj(self):
        client = boto3.client('ecs', region_name='eu-west-1')
        _ = client.create_cluster(
            clusterName='test_ecs_cluster'
        )
        _ = client.register_task_definition(
            family='test_ecs_task',
            containerDefinitions=[
                {
                    'name': 'hello_world',
                    'image': 'docker/hello-world:latest',
                    'cpu': 1024,
                    'memory': 400,
                    'essential': True,
                    'environment': [{
                        'name': 'AWS_ACCESS_KEY_ID',
                        'value': 'SOME_ACCESS_KEY'
                    }],
                    'logConfiguration': {'logDriver': 'json-file'}
                }
            ]
        )
        response = client.describe_task_definition(
            taskDefinition='test_ecs_task'
        )
        assert response['taskDefinition']['containerDefinitions'][0]['name'] == 'hello_world'

    @moto.mock_ecs
    def test_describe_service(self):
        client = boto3.client('ecs', region_name='eu-west-1')
        _ = client.create_cluster(
            clusterName='test_ecs_cluster'
        )
        _ = client.register_task_definition(
            family='test_ecs_task',
            containerDefinitions=[
                {
                    'name': 'hello_world',
                    'image': 'docker/hello-world:latest',
                    'cpu': 1024,
                    'memory': 400,
                    'essential': True,
                    'environment': [{
                        'name': 'AWS_ACCESS_KEY_ID',
                        'value': 'SOME_ACCESS_KEY'
                    }],
                    'logConfiguration': {'logDriver': 'json-file'}
                }
            ]
        )
        _ = client.create_service(
            cluster='test_ecs_cluster',
            serviceName='test_ecs_service1',
            taskDefinition='test_ecs_task',
            desiredCount=2
        )
        response = client.describe_services(
            cluster='test_ecs_cluster',
            services=['test_ecs_service1']
        )
        assert response['services'][0]['serviceName'] == 'test_ecs_service1'

    @moto.mock_ec2
    @moto.mock_ecs
    def test_get_tasks(self):
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
        container_instance_ids = list(map((lambda x: x.split('/')[1]), test_instance_arns))
        _ = ecs_client.register_task_definition(
            family='test_ecs_task',
            containerDefinitions=[
                {
                    'name': 'hello_world',
                    'image': 'docker/hello-world:latest',
                    'cpu': 1024,
                    'memory': 400,
                    'essential': True,
                    'environment': [{
                        'name': 'AWS_ACCESS_KEY_ID',
                        'value': 'SOME_ACCESS_KEY'
                    }],
                    'logConfiguration': {'logDriver': 'json-file'}
                }
            ]
        )
        _ = ecs_client.start_task(
            cluster='test_ecs_cluster',
            taskDefinition='test_ecs_task',
            overrides={},
            containerInstances=container_instance_ids,
            startedBy='foo'
        )
        _ = ecs_client.create_service(
            cluster='test_ecs_cluster',
            serviceName='test_ecs_service1',
            taskDefinition='test_ecs_task',
            desiredCount=3
        )
        response = ecs_client.list_tasks(
            cluster='test_ecs_cluster',
            serviceName='test_ecs_service1'
        )
        assert len(response['taskArns']) == 3

    @moto.mock_ec2
    @moto.mock_ecs
    def test_get_all_tasks(self):
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
        _ = ecs_client.register_task_definition(
            family='test_ecs_task',
            containerDefinitions=[
                {
                    'name': 'hello_world',
                    'image': 'docker/hello-world:latest',
                    'cpu': 1024,
                    'memory': 400,
                    'essential': True,
                    'environment': [{
                        'name': 'AWS_ACCESS_KEY_ID',
                        'value': 'SOME_ACCESS_KEY'
                    }],
                    'logConfiguration': {'logDriver': 'json-file'}
                }
            ]
        )
        tasks_arns = [
            task['taskArn'] for task in ecs_client.run_task(
                cluster='test_ecs_cluster',
                overrides={},
                taskDefinition='test_ecs_task',
                count=2,
                startedBy='moto'
            )['tasks']
        ]
        response = ecs_client.describe_tasks(
            cluster='test_ecs_cluster',
            tasks=tasks_arns
        )
        assert len(response['tasks']) == 2

    @moto.mock_ecs
    def test_update_service(self):
        ecs_client = boto3.client('ecs', region_name='eu-west-1')
        _ = ecs_client.create_cluster(
            clusterName='test_ecs_cluster'
        )
        _ = ecs_client.register_task_definition(
            family='test_ecs_task',
            containerDefinitions=[
                {
                    'name': 'hello_world',
                    'image': 'docker/hello-world:latest',
                    'cpu': 1024,
                    'memory': 400,
                    'essential': True,
                    'environment': [{
                        'name': 'AWS_ACCESS_KEY_ID',
                        'value': 'SOME_ACCESS_KEY'
                    }],
                    'logConfiguration': {'logDriver': 'json-file'}
                }
            ]
        )
        response = ecs_client.create_service(
            cluster='test_ecs_cluster',
            serviceName='test_ecs_service',
            taskDefinition='test_ecs_task',
            desiredCount=2
        )
        assert response['service']['desiredCount'] == 2
        response = ecs_client.update_service(
            cluster='test_ecs_cluster',
            service='test_ecs_service',
            taskDefinition='test_ecs_task',
            desiredCount=0
        )
        assert response['service']['desiredCount'] == 0

    @moto.mock_ecs
    def test_new_task_definition(self):
        ecs_client = boto3.client('ecs', region_name='eu-west-1')
        response = ecs_client.register_task_definition(
            family='test_ecs_task',
            containerDefinitions=[
                {
                    'name': 'hello_world',
                    'image': 'docker/hello-world:latest',
                    'cpu': 1024,
                    'memory': 400,
                    'essential': True,
                    'environment': [{
                        'name': 'AWS_ACCESS_KEY_ID',
                        'value': 'SOME_ACCESS_KEY'
                    }],
                    'logConfiguration': {'logDriver': 'json-file'}
                }
            ]
        )
        assert response['taskDefinition']['containerDefinitions'][
        0]['name'] == 'hello_world'

    def _test__success_condition(self, svcobj, tarn, otasks):
        svc = svcobj['services'][0]
        if svc['taskDefinition'] != tarn:
            return False
        if svc['desiredCount'] != svc['runningCount']:
            return False
        if svc['pendingCount'] != 0:
            return False
        if len(otasks) != 0:
            return False
        return True

    @pytest.mark.parametrize('svcobj, tarn, otasks, expected', [
        ({'services': [{'taskDefinition': 'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:518',
                        'desiredCount': 2,
                        'pendingCount': 0,
                        'runningCount': 2}]},
         'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:515',
         ['task'],
         False),
        ({'services': [{'taskDefinition': 'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:518',
                        'desiredCount': 2,
                        'pendingCount': 1,
                        'runningCount': 1}]},
         'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:518',
         ['task'],
         False),
        ({'services': [{'taskDefinition': 'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:518',
                        'desiredCount': 2,
                        'pendingCount': 1,
                        'runningCount': 2}]},
         'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:518',
         ['task'],
         False),
        ({'services': [{'taskDefinition': 'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:518',
                        'desiredCount': 2,
                        'pendingCount': 0,
                        'runningCount': 2}]},
         'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:518',
         ['task'],
         False),
        ({'services': [{'taskDefinition': 'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:518',
                        'desiredCount': 2,
                        'pendingCount': 0,
                        'runningCount': 2}]},
         'arn:aws:ecs:eu-west-1:xxxxxxxxxx:task-definition/ddm_task_dev:518',
         [],
         True),
    ])
    def test_check_ami_id_format(self, svcobj, tarn, otasks, expected):
        assert self._test__success_condition(svcobj, tarn, otasks) == expected
