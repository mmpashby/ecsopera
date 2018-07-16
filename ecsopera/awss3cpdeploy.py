# pylint: disable=C0111,C0103,C1801,R0902,R0913,R0201,W0511,W0622
import os
import re
from datetime import datetime
import urllib.parse
from botocore.exceptions import ClientError
import boto3
from ecsopera.raiseexception import exception_handler


class AWSS3CpDeploy(object):
    """
    A class to assist with the copying of objects to s3 and cloudfront ops.
    """
    def __init__(self, akey, skey, source, destination, expires,
                 cflistdistid, max_age, cleardst, invalcache, timeout, log):
        self.accesskey = akey
        self.secretkey = skey
        self.s = self.boto_session(akey, skey)
        self.source = source
        self.destination = destination
        self.expires = expires
        self.cflistid = cflistdistid
        self.maxage = max_age
        self.cleardst = cleardst
        self.invalcache = invalcache
        self.timeout = timeout
        self.jobruntime = 0
        self.log = log

    @staticmethod
    def boto_session(akey, skey):
        """Create Boto Session Object."""
        return boto3.session.Session(aws_access_key_id=akey,
                                     aws_secret_access_key=skey)

    @exception_handler(errors=(ClientError,))
    def invalidate_cf_dist(self, id, origin):
        """Invalidate cloudfront distribution."""
        s3dstcheck = re.match(r'(s3://)([\w\.-]{3,63})', origin, re.I)
        self.log.info(s3dstcheck.group(2))
        if s3dstcheck:
            self.log.info("Found bucket origin for cf invalidation...")
        else:
            raise SystemExit("Bucket origin does not exist...")
        s3 = boto3.resource('s3')
        dst_bucket = s3.Bucket(s3dstcheck.group(2))
        objects = [urllib.parse.quote_plus(o.key)
                   for o in dst_bucket.objects.all()]
        cf = self.s.client('cloudfront')
        cf.create_invalidation(DistributionId=id,
                               InvalidationBatch={
                                   'Paths': {
                                       'Quantity': 1,
                                       'Items': ['/*']},
                                   'CallerReference': 'ref-{0}'.format(
                                       datetime.now())
                               })
        return True

    @exception_handler(errors=(ClientError,))
    def copy_obj_action(self, src, dst, exp, maxage, cleardst):
        """Perform s3cp from local absolute src to bucket."""
        s3 = self.s.resource('s3')
        ex_args = {'CacheControl': 'public, max-age={0}'.format(maxage)}
        if exp:
            self.log.info("Specified expires, but max-age wins. Unlucky.")
        if cleardst:
            self.log.info("Clearing destination bucket objects...")
            # dst_bucket.objects.all().delete()
            self.log.info("All destination bucket objects removed...")
        for root, _, files in os.walk(src):
            for filename in files:
                # construct local path
                localp = os.path.join(root, filename)
                # construct relative path
                relpath = os.path.relpath(localp, src)
                self.log.info("Uploading files...")
                s3.meta.client.upload_file(localp,
                                           dst,
                                           relpath,
                                           ExtraArgs=ex_args)
                self.log.info("{0} copied to {1}".format(localp, relpath))
        self.log.info("All files copied from local to dst bucket...")
        return True

    @exception_handler(errors=(ClientError,))
    def copy_s3obj_action(self, src, dst, exp, maxage, cleardst):
        """Perform s3cp from bucket to bucket."""
        s3 = self.s.resource('s3')
        src_bucket = s3.Bucket(src)
        ex_args = {'CacheControl': 'public, max-age={0}'.format(maxage)}
        if exp:
            self.log.info("Specified expires, but max-age wins. Unlucky.")
        if cleardst:
            self.log.info("Clearing destination bucket objects...")
            # dst_bucket.objects.all().delete()
            self.log.info("All destination bucket objects removed...")
        for obj in src_bucket.objects.filter():
            copy_source = {'Bucket': src,
                           'Key': obj.key}
            s3.meta.client.copy(copy_source, dst, obj.key, ExtraArgs=ex_args)
        return True

    def s3cp_control(self, src, dst, exp, maxage, cleardst):
        """
           Identify object source and resolve control flow.
        """
        # check if source and dst is an s3 bucket.
        # TODO: check if bucket name has period and hyphen adjacent to each
        # other.
        s3srccheck = re.match(r'(s3://)([\w\.-]{3,63})', src, re.I)
        s3dstcheck = re.match(r'(s3://)([\w\.-]{3,63})', dst, re.I)
        if s3srccheck and s3dstcheck:
            self.log.info('bucket source path detected.')
            self.log.info('s3cp job starting...')
            if self.copy_s3obj_action(s3srccheck.group(2),
                                      s3dstcheck.group(2),
                                      exp,
                                      maxage,
                                      cleardst):
                self.log.info("s3cp bucket to bucket complete...")
            else:
                self.log.error("s3cp bucket to bucket failed...")
                raise SystemExit("Job Cancelled...Exit")
            return True
        # check if source exists. this should be the abs path and doesn't
        # care if file or dir.
        elif os.path.exists(src) and os.path.isdir(src) and s3dstcheck:
            self.log.info('source dir exists.')
            if self.copy_obj_action(src,
                                    s3dstcheck.group(2),
                                    exp,
                                    maxage,
                                    cleardst):
                self.log.info("s3cp src dir to bucket complete...")
            else:
                self.log.error("src dir to bucket failed...")
                raise SystemExit("Job Cancelled...Exit")
            return True
        return False

    def s3cp_deploy_init(self):
        """deploy_init: Call this method to begin a new s3cp deployment."""
        self.log.info("Creating s3cp job....")
        self.log.info("Launch s3cp control flow...")
        if not self.s3cp_control(self.source,
                                 self.destination,
                                 self.expires,
                                 self.maxage,
                                 self.cleardst):
            self.log.error("s3cp control flow could not resolve request...")
            raise SystemExit("Job Cancelled...Exit")
        else:
            self.log.info("s3cp job complete...")
        if self.invalcache:
            self.log.info("Creating cloudfront distribution invalidation...")
            if not self.invalidate_cf_dist(self.cflistid,
                                           self.destination):
                self.log.error("Cloudfront Invalidation failed...")
                raise SystemExit("Job Cancelled...Exit")
            else:
                self.log.info("Cloundfront Invalidation Started...")
        else:
            self.log.info("No Cloudfront Invalidation Required...")
        self.log.info("Job Finished!!!!...")
