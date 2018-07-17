# pylint: disable=C0111,C0103,C1801,R0902,R0913,R0201,W0622
import sys
from ecsopera.awsamiupdate import AWSECSAmiUpdate
from ecsopera.awsecsdeploy import AWSECSDeploy
from ecsopera.version import __version__


def get_version(log):
    """Get ECSOpera Version."""
    log.cmdname = 'version'
    log.display_banner()
    print("Version: {0}".format(__version__))


def aws_ecs_ami_update(akey, skey, ami, cluster, lcname, timeout, log):
    """AMI Update command."""
    log.cmdname = 'aws-ecs-amiupdate:'
    log.display_banner()
    if ami is None or cluster is None or lcname is None:
        log.error("### You have not provided a value for servicename/cluster/"
                  "ami. Safely Exiting.... ###")
        sys.exit(0)
    amiupdate = AWSECSAmiUpdate(akey, skey, ami, cluster, lcname, timeout, log)
    amiupdate.ami_rollout_init()


def aws_ecs_deploy(akey, skey, servicename, cluster,
                   image, dcount, min, max, timeout, log):
    """ECS Deploy Command."""
    log.cmdname = 'aws-ecs-deploy:'
    log.display_banner()
    if servicename is None or cluster is None or image is None:
        log.error("You have not provided an option value for servicename/"
                  "cluster/image...")
        sys.exit(0)
    ecsdeploy = AWSECSDeploy(akey, skey, servicename, cluster, image,
                             dcount, min, max, timeout, log)
    ecsdeploy.task_deploy_init()

