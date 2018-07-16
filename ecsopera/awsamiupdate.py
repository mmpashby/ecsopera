# pylint: disable=C0111,C0103,C1801,R0902,R0913,R0201,W0622
import base64
import time
import re
from itertools import groupby
import progressbar
import boto3
from botocore.exceptions import ClientError
from ecsopera.raiseexception import exception_handler


class AWSECSAmiUpdate(object):
    """A class to assist with updating an AMI"""

    def __init__(self, akey, skey, ami, cluster, lcname, timeout, log):
        self.accesskey = akey
        self.secretkey = skey
        self.s = self.boto_session(akey, skey)
        self.ami = self.check_ami_id_format(ami)
        self._cluster = cluster
        self._lcname = lcname
        self._timeout = timeout
        self.log = log
        self.newamiobj = self.get_ami()
        self.cinstances = self.get_ecs_container_instances()
        self.ec2instances = self.get_ecs_instance_id()
        self.currentamis = self.get_ecs_instance_amiid()
        self.currentlc = self.get_asg_launch_conf()
        self.currentasgs = self.get_asgs()
        self.asgicount = self._get_asg_instance_count()
        self.updateasgcount = 0
        self.copiedlc = self.create_asg_launch_conf(self.currentlc,
                                                    newlc=False,
                                                    ami=None, itype=None)
        self.rdyscaled = False
        self.idrained = False
        self.newitime = 0
        self.draintime = 0

    @staticmethod
    def boto_session(akey, skey):
        return boto3.session.Session(aws_access_key_id=akey,
                                     aws_secret_access_key=skey)

    @staticmethod
    def check_ami_id_format(amiid):
        """Check if AMI is in correct format or raise exception."""
        ami = str(amiid)
        id_check = re.match(r'ami-\w{8,17}', ami, re.M | re.I)
        if id_check is None:
            raise ValueError("AMI is not in correct format,"
                             "please check ami-id and try again.")
        else:
            return ami

    @property
    def cluster(self):
        return self._cluster

    @cluster.setter
    def cluster(self, cluster):
        self._cluster = cluster

    @property
    def lcname(self):
        return self._lcname

    @lcname.setter
    def lcname(self, lcname):
        self._lcname = lcname

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout

    @exception_handler(errors=(ClientError,))
    def get_ami(self):
        """Return AMI information from passed ami id list."""
        return self.s.client('ec2').describe_images(ImageIds=[self.ami])

    @exception_handler(errors=(ClientError, KeyError))
    def get_ecs_container_instances(self):
        """Return STATUS x container instances from ECS cluster."""
        return self.s.client('ecs').list_container_instances(
            cluster=self._cluster,
            status='ACTIVE')['containerInstanceArns']

    @exception_handler(errors=(ClientError, KeyError))
    def get_ecs_instance_id(self):
        """Return ecs instance ids from ECS cluster."""
        ci = self.s.client('ecs').describe_container_instances(
            cluster=self._cluster,
            containerInstances=self.cinstances)
        return [i['ec2InstanceId'] for i in ci['containerInstances']]

    @exception_handler(errors=(ClientError, IndexError, KeyError))
    def get_ecs_instance_amiid(self):
        """Return sorted and grouped AMI ids from passed instances."""
        res_ci = self.s.client('ec2').describe_instances(
            InstanceIds=self.ec2instances)['Reservations']
        instances = sum([[i for i in r['Instances']] for r in res_ci], [])
        sorted_amis = groupby([i['ImageId'] for i in instances])
        return [ami[0] for ami in sorted_amis]

    @exception_handler(errors=(ClientError, IndexError, KeyError))
    def get_asg_launch_conf(self):
        """Return Launch Configuration object from LC name."""
        return self.s.client('autoscaling').describe_launch_configurations(
            LaunchConfigurationNames=[self._lcname])['LaunchConfigurations'][0]

    @exception_handler(errors=(ClientError, KeyError))
    def get_asgs(self):
        """Return managed ASGs that are from LC name."""
        asgs = self.s.client('autoscaling').describe_auto_scaling_groups()['AutoScalingGroups']
        return [asg for asg in asgs if asg['LaunchConfigurationName'] ==
                self._lcname]

    @exception_handler(errors=(ClientError, KeyError))
    def create_asg_launch_conf(self, currentlc, newlc, ami, itype):
        """Create Launch Configuration based on passed args."""
        if newlc:
            newlcname = currentlc['LaunchConfigurationName']
        else:
            newlcname = '{0}-copy'.format(currentlc['LaunchConfigurationName'])
        if ami is not None:
            image = ami
        else:
            image = currentlc['ImageId']
        if itype is not None:
            nitype = itype
        else:
            nitype = currentlc['InstanceType']
        return self.s.client('autoscaling').create_launch_configuration(
            LaunchConfigurationName=newlcname,
            ImageId=image,
            KeyName=currentlc['KeyName'],
            SecurityGroups=currentlc['SecurityGroups'],
            UserData=base64.b64decode(currentlc['UserData']),
            InstanceType=nitype,
            IamInstanceProfile=currentlc['IamInstanceProfile'],
            InstanceMonitoring=currentlc['InstanceMonitoring'],
            EbsOptimized=currentlc['EbsOptimized'])

    @exception_handler(errors=(ClientError,))
    def update_asg_launch_conf(self, currentasg, lcname):
        """Update passed ASG with specified LC."""
        return self.s.client('autoscaling').update_auto_scaling_group(
            AutoScalingGroupName=currentasg['AutoScalingGroupName'],
            LaunchConfigurationName=lcname)

    @exception_handler(errors=(ClientError, KeyError))
    def get_running_task_count(self):
        """
        Return running task count in passed cluster and container instances.
        """
        rinstances = self.s.client('ecs').describe_container_instances(
            cluster=self._cluster,
            containerInstances=self.cinstances)['containerInstances']
        rtask_count = 0
        for i in rinstances:
            rtask_count += i['runningTasksCount']
        return rtask_count

    @exception_handler(errors=(ClientError,))
    def create_asg(self, currentasg):
        """Create ASG based on passed current ASG parameters and LC name."""
        return self.s.client('autoscaling').create_auto_scaling_group(
            AutoScalingGroupName='ASG-{0}'.format(int(time.time())),
            LaunchConfigurationName=self._lcname,
            MinSize=currentasg['MinSize'],
            MaxSize=currentasg['MaxSize'],
            DesiredCapacity=currentasg['DesiredCapacity'],
            VPCZoneIdentifier=currentasg['VPCZoneIdentifier'],
            HealthCheckGracePeriod=currentasg['HealthCheckGracePeriod'])

    @exception_handler(errors=(ClientError,))
    def delete_asg(self, asgname):
        """Delete specified ASG."""
        return self.s.client('autoscaling').delete_auto_scaling_group(
            AutoScalingGroupName=asgname,
            ForceDelete=True)

    @exception_handler(errors=(ClientError,))
    def delete_launch_conf(self, lcname):
        """Delete specified LC."""
        return self.s.client('autoscaling').delete_launch_configuration(
            LaunchConfigurationName=lcname)

    @exception_handler(errors=(ClientError,))
    def drain_ecs_container_instances(self):
        """
        Drains container instances specified by passed container instances.
        """
        return self.s.client('ecs').update_container_instances_state(
            cluster=self._cluster,
            containerInstances=self.cinstances,
            status='DRAINING')

    def _get_asg_instance_count(self):
        asg_i_count = 0
        for asg in self.currentasgs:
            asg_i_count += len(asg['Instances'])
        return asg_i_count

    def _update_asg_lconf(self):
        for asg in self.currentasgs:
            self.update_asg_launch_conf(asg, '{0}-copy'.format(self._lcname))
            self.updateasgcount += 1

    def _upscale_asgs(self):
        for asg in self.currentasgs:
            self.create_asg(asg)

    def _poll_new_cinstances(self):
        scale_bar = progressbar.ProgressBar(
            max_value=progressbar.UnknownLength)
        while not self.rdyscaled:
            if self.newitime >= self._timeout:
                return False
            sinstances = self.get_ecs_container_instances()
            if len(self.cinstances) * 2 == len(sinstances):
                self.rdyscaled = True
                return True
            scale_bar.update(self.newitime)
            self.log.info("Polling ECS Cluster For New Container Instances"
                          ".....")
            self.newitime += 5
            time.sleep(5)

    def _drain_old_cinstances(self):
        drain_bar = progressbar.ProgressBar(
            max_value=progressbar.UnknownLength)
        self.log.info('Draining Existing Container Instances.....')
        while not self.idrained:
            if self.draintime >= self._timeout:
                return False
            dinstances = self.get_running_task_count()
            if dinstances == 0:
                self.idrained = True
                self.log.info("Drained Instances Tasks Have Been Shifted"
                              "....Finishing....")
                return True
            drain_bar.update(self.draintime)
            self.log.info('Draining Container Instances.....')
            self.draintime += 5
            time.sleep(5)

    def _delete_old_asgs(self):
        for asg in self.currentasgs:
            self.delete_asg(asg['AutoScalingGroupName'])

    def ami_rollout_init(self):
        """
        ami_rollout_init: Call this method to perform an ami rollout to
        defined, ECS container cluster."""
        self.log.info('Creating AWS ECS AMI Update Job...')
        self.log.info('Found {0} Container Instances: {1}'.format(
            len(self.cinstances), self.cinstances))
        self.log.info('Found the Common AMI-Images: {0}'.format(
            self.currentamis))
        self.log.info('Found the following ASGs to operate on: {0}'.format(
            [i['AutoScalingGroupName'] for i in self.currentasgs]))
        self.log.info('Copied Launch Configuration {0}...'.format(
            self.currentlc))
        self.log.info('Found {0} instances inside corresponding ASGs'.format(
            self.asgicount))
        self._update_asg_lconf()
        self.log.info('Updated {0} ASGs with copied LC.....'.format(
            self.updateasgcount))
        self.delete_launch_conf(self._lcname)
        self.log.info('Deleted LC: {0}'.format(self._lcname))
        self.create_asg_launch_conf(self.currentlc,
                                    newlc=True,
                                    ami=self.ami,
                                    itype=None)
        self.log.info('Created new LC.....')
        self.log.info('Doubling Up ASG count.....')
        self._upscale_asgs()
        if not self._poll_new_cinstances():
            self.log.error("Timeout reached on checking for healthy running"
                           "container instances. Rollback needed....")
            raise SystemExit('Job Cancelled...Exit')
        self.log.info('New Member Container Instances Found....Finishing...')
        self.drain_ecs_container_instances()
        if not self._drain_old_cinstances():
            self.log.error("Timeout reached on draining running tasks on old"
                           "instances. Rollback needed....")
            raise SystemExit('Job Cancelled...Exit')
        self._delete_old_asgs()
        self.log.info('In process of deleting old ASG container instances....')
        self.delete_launch_conf('{0}-copy'.format(self._lcname))
        self.log.info('Finished AMI Updating ECS!!!!!')
