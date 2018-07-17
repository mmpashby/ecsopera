import sys
import logging
import click
from ecsopera.awscommands import (get_version,
                                   aws_ecs_ami_update,
                                   aws_ecs_deploy)
                                   
from ecsopera.loghelper import LogHelper


@click.group()
@click.pass_context
@click.option('--awsaccesskey',
              envvar='AWS_ACCESS_KEY_ID',
              default=None,
              type=str)
@click.option('--awssecretkey',
              envvar='AWS_SECRET_ACCESS_KEY',
              default=None,
              type=str)
@click.option('--awsregion',
              envvar='AWS_DEFAULT_REGION',
              default=None,
              type=str)
@click.option('--debug',
              is_flag=True,
              help="Debug mode for true verbose output.")
def ecsopera(ecsoperaaccess, awsaccesskey, awssecretkey, awsregion, debug):
    # TODO: Create decorator or better way of dealing with different
    # providers in future.
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    log = LogHelper(stream=sys.stdout,
                    level=log_level,
                    fmt='%(asctime)s %(levelname)s %(message)s')
    if awsaccesskey is None or awssecretkey is None or awsregion is None:
        log.error("No provided value for awsaccesskey/awssecretkey/awsregion."
                  "Safely Exiting....")
        sys.exit(0)
    ecsoperaaccess.obj = {'accesskey': awsaccesskey,
                           'secretkey': awssecretkey,
                           'region': awsregion,
                           'logger': log}


@click.command('version',
               short_help="Get the current version number.")
@click.pass_obj
def version(ecsoperaaccess):
    get_version(ecsoperaaccess['logger'])


@click.command('aws-ecs-amiupdate',
               short_help='Update the container instance AMI.')
@click.option('--ami', help="The AMI image to ++ to.", default=None, type=str)
@click.option('--cluster',
              help="The ECS cluster name to operate on.",
              default=None, type=str)
@click.option('--launchcfg',
              help="The Launch Configuration name to operate on.",
              default=None,
              type=str)
@click.option('--timeout',
              help="Timeout (s) value for spinning up new container instances "
                   "and performing draining on existing instances. "
                   "(default 300s (5 mins)).",
              default=300,
              type=int)
@click.pass_obj
def aws_amiupdate(ecsoperaaccess, ami, cluster, launchcfg, timeout):
    aws_ecs_ami_update(ecsoperaaccess['accesskey'],
                       ecsoperaaccess['secretkey'],
                       ami,
                       cluster,
                       launchcfg,
                       timeout,
                       ecsoperaaccess['logger'])


@click.command('aws-ecs-deploy',
               short_help="Use this command to deploy a new task definition "
                          "to a specified ECS service.")
@click.option('--servicename',
              help="The ECS service name to operate on.",
              default=None, type=str)
@click.option('--cluster',
              help="The ECS cluster name to operate on.",
              default=None,
              type=str)
@click.option('--image',
              help="The Docker Image Repo location.",
              default=None,
              type=str)
@click.option('--desiredcount',
              help="The number of instantiations of the task to place "
                   "and keep running in your service.",
              default=2,
              type=int)
@click.option('--min',
              help="minumumHealthyPercent: The lower limit on the number of "
                   "running tasks during a deployment. (default: 100)",
              default=100,
              type=int)
@click.option('--max',
              help="maximumPercent: The upper limit on the number of running "
                   "tasks during a deployment. (default: 200)",
              default=200,
              type=int)
@click.option('--timeout',
              help="Timeout value for checking for successful deployment. "
                   "(default 5 mins).",
              default=300,
              type=int)
@click.pass_obj
def aws_ecsdeploy(ecsoperaaccess,
                  servicename,
                  cluster,
                  image,
                  desiredcount,
                  min,
                  max,
                  timeout):
    aws_ecs_deploy(ecsoperaaccess['accesskey'],
                   ecsoperaaccess['secretkey'],
                   servicename,
                   cluster,
                   image,
                   desiredcount,
                   min,
                   max,
                   timeout,
                   ecsoperaaccess['logger'])

# Provider Commands
ecsopera.add_command(version)
ecsopera.add_command(aws_amiupdate)
ecsopera.add_command(aws_ecsdeploy)

if __name__ == "__main__":
    ecsopera()
