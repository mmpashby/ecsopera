# pylint: disable=C0111,C0103,C1801,R0902,R0913,R0201,W0622
import sys
from ecsopera.awsamiupdate import AWSECSAmiUpdate
from ecsopera.awsecsdeploy import AWSECSDeploy
from ecsopera.awss3cpdeploy import AWSS3CpDeploy
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


def aws_s3cp_cloudfront_deploy(akey, skey, source, destination, expires,
                               cflistdistid, maxage, cleardst, invalcache,
                               timeout, log):
    """AWS S3 Copy Command & Cloudfront post operations."""
    log.cmdname = 'aws-s3cpcloudfront-deploy:'
    log.display_banner()
    if source is None:
        log.error("You have not specified a source. You must supply a source "
                  "local folder or s3-bucket.")
        sys.exit(0)
    if destination is None:
        log.error("You have not specified a destination s3 bucket. You must "
                  "specify a destination s3 bucket for copy operation.")

    s3cpdeploy = AWSS3CpDeploy(akey, skey, source, destination, expires,
                               cflistdistid, maxage, cleardst, invalcache,
                               timeout, log)
    s3cpdeploy.s3cp_deploy_init()
