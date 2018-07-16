# pylint: disable=C0111,C0103,C1801,R0902,R0913,R0201,W0622
import time
from botocore.exceptions import ClientError
import boto3
import progressbar
from ecsopera.raiseexception import exception_handler


class AWSECSDeploy(object):
    """A class to assist with deploying a new image to an ECS service."""
    # We Get that we should probably break this out into multiple objects
    # and find a better model.
    def __init__(self, akey, skey, servicename, cluster,
                 image, dcount, min, max, timeout, log):
        self.accesskey = akey
        self.secretkey = skey
        self.s = self.boto_session(akey, skey)
        self.servicename = servicename
        self.cluster = cluster
        self.image = image
        self.dcount = dcount
        self.mintaskcount = min
        self.maxtaskcount = max
        self.timeout = timeout
        self.deployconf = {'maximumPercent': self.maxtaskcount,
                           'minimumHealthyPercent': self.mintaskcount}
        self.currenttaskarn = self.get_service_task_arn(self.cluster,
                                                        self.servicename)
        self.currenttaskobj = self.get_service_task_obj(self.currenttaskarn)
        task_def = self.currenttaskobj['taskDefinition']
        self.currenttaskimage = task_def['containerDefinitions'][0]['image']
        self.newtaskobj = self.currenttaskobj['taskDefinition']
        self.newtaskfamily = self.newtaskobj['family']
        self.newtaskrolearn = self.newtaskobj['taskRoleArn']
        self.newcontdef = self.newtaskobj['containerDefinitions']
        self.newcontdef[0]['image'] = self.image
        self.jobruntime = 0
        self.log = log
        self.newtaskdeployed = False
        self.regtaskobj = None
        self.regtaskarn = None
        self.newserviceobj = None

    @staticmethod
    def boto_session(akey, skey):
        """Create Boto Session Object."""
        return boto3.session.Session(aws_access_key_id=akey,
                                     aws_secret_access_key=skey)

    @exception_handler(errors=(ClientError, IndexError, KeyError))
    def get_service_task_arn(self, cluster, sname):
        """
        Return the ARN of the current task from parsed cluster
        and service name.
        """
        svc = self.s.client('ecs').describe_services(cluster=cluster,
                                                     services=[sname])
        return svc['services'][0]['taskDefinition']

    @exception_handler(errors=(ClientError,))
    def get_service_task_obj(self, tarn):
        """Return the Task Object from the parsed task ARN."""
        return self.s.client('ecs').describe_task_definition(taskDefinition=tarn)

    @exception_handler(errors=(ClientError,))
    def describe_service(self, cluster, sname):
        """Return service object from parsed service name."""
        return self.s.client('ecs').describe_services(cluster=cluster,
                                                      services=[sname])

    @exception_handler(errors=(ClientError,))
    def get_tasks(self, cluster, service):
        """Get the running tasks from the provided cluster and service."""
        return self.s.client('ecs').list_tasks(cluster=cluster,
                                               serviceName=service)

    @exception_handler(errors=(ClientError, KeyError))
    def get_all_tasks(self, cluster, tasks):
        """Return and describe all tasks from cluster and task arns."""
        return self.s.client('ecs').describe_tasks(
            cluster=cluster, tasks=tasks)['tasks']

    @exception_handler(errors=(ClientError,))
    def update_service(self, cluster, service, tarn, dc, depstrat):
        """Update the specified service with parsed task
        and deployment strategy."""
        return self.s.client('ecs').update_service(cluster=cluster,
                                                   service=service,
                                                   taskDefinition=tarn,
                                                   desiredCount=dc,
                                                   deploymentConfiguration=depstrat)

    @exception_handler(errors=(ClientError,))
    def reg_new_task_definition(self, fam, tarn, cdef):
        """Register New Task under parsed family."""
        return self.s.client('ecs').register_task_definition(family=fam,
                                                             taskRoleArn=tarn,
                                                             containerDefinitions=cdef)

    def _describe_service(self):
        return self.describe_service(self.cluster, self.servicename)

    def _get_tasks(self):
        return self.get_tasks(self.cluster, self.servicename)['taskArns']

    def _get_all_tasks(self, rtarns):
        return self.get_all_tasks(self.cluster, rtarns)

    def _success_condition(self, svcobj, otasks, tarn):
        """
        _success_condition: Internal method to check multiple deploy success
         conditions:-
           - current service definition must == the registered task definition.
           - current service desired count must == the current service running
             count.
           - current service must have 0 pending tasks.
           - there must be 0 running not specified registered tasks
           (tagged as old tasks).
        """
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

    def _poll_new_task(self, tarn):
        """
        _poll_new_task: Internal method for polling ECS service for
        running tasks.
        """
        newtask_bar = progressbar.ProgressBar(
            max_value=progressbar.UnknownLength)
        while not self.newtaskdeployed:
            if self.jobruntime >= self.timeout:
                return False
            r_service = self._describe_service()
            r_tasks_arns = self._get_tasks()
            self.log.info("Following tasks found (use to troubleshoot):"
                          "{0}".format(r_tasks_arns))
            r_tasks = self._get_all_tasks(r_tasks_arns)
            reg_task_arn = tarn
            o_tasks = [i for i in r_tasks if i['taskDefinitionArn'] != reg_task_arn]
            if self._success_condition(r_service, o_tasks, reg_task_arn):
                self.newtaskdeployed = True
                return True
            newtask_bar.update(self.jobruntime)
            self.log.info("Polling for new task deployment....")
            self.jobruntime += 5
            time.sleep(5)

    def _task_rollback(self):
        """
        _task_rollback: Internal method for rolling back a failed
        task deployment.
        """
        self.log.info("Task rollback in progress...")
        self.log.info("Rolling back {0} service to task def {1}".format(
            self.servicename,
            self.currenttaskarn))
        self.update_service(self.cluster,
                            self.servicename,
                            self.currenttaskarn,
                            self.dcount,
                            self.deployconf)
        self.log.info("Service {0} has been rolled back".format(
            self.servicename))
        return bool(self._poll_new_task(self.currenttaskarn))

    def task_deploy_init(self):
        """deploy_init: Call this method to begin a new ECS Task Deployment."""
        self.log.info("Starting New Task Deployment....")
        self.log.info("Found Current Task Def Image {0}".format(
            self.currenttaskimage))
        self.log.info("Registering new task definition under family"
                      "{0}....".format(self.newtaskfamily))
        self.regtaskobj = self.reg_new_task_definition(self.newtaskfamily,
                                                       self.newtaskrolearn,
                                                       self.newcontdef)
        self.regtaskarn = self.regtaskobj['taskDefinition']['taskDefinitionArn']
        self.log.info("Updating {0} service......".format(self.servicename))
        self.newserviceobj = self.update_service(self.cluster,
                                                 self.servicename,
                                                 self.regtaskarn,
                                                 self.dcount,
                                                 self.deployconf)
        self.log.info("Service {0} Updated".format(self.servicename))
        self.log.info("Sleeping for 60 secs before polling cluster for"
                      "new task....")
        time.sleep(60)
        self.log.info("Polling cluster for newly deployed task.. ###")
        if self._poll_new_task(self.regtaskobj['taskDefinition']
                               ['taskDefinitionArn']):
            self.log.info("Finished ECS Deploy")
        else:
            self.log.error("""Timeout reached on checking for healthy running new task.
                           Rollback needed ....""")
            self.jobruntime = 0
            if self._task_rollback():
                self.log.info("Rollback Succeeded")
            else:
                raise SystemExit("Rollback Failed (check AWS console)....")
