# ecsopera


#### AWS ECS Container Orchestration Tooling to update and resize container instances.

##### Key Features
- [x] Replace AMI images of underlying Container Instances with a horizontal scale out.
- [x] Update the task definition version of a defined service.


##### Requirements
- Python3.x required
- Recommend install in virtualenv (sudo not needed then)

##### Install (TODO: PyPy server location)

```bash
git clone git@github.com:Pashbee/ecsopera.git 
cd ecsopera/
pip3 install .
```

##### Dev Install

To contribute we recommend installing in dev mode using:-

```bash
git clone git@github.com:Pashbee/ecsopera.git 
cd ecsopera/
pip3 install -e .
```

To run unit tests:-

```pytest```

##### Pre-req

To use for AWS ECS you will need the pragmatic keys provided by your account access.

You will need to set your keys as either env vars, like so:-

```bash
export AWS_ACCESS_KEY_ID=xxxxxxxx
export AWS_SECRET_ACCESS_KEY=xxxxxxxxxx
export AWS_DEFAULT_REGION=eu-west-1
```

......or pass them as flags using ```--awsaccesskey ``` and ```--awssecretkey  ``` and ```---awsregion```

##### Help

To get help for any of the multi staged commands that ecsopera provides use the ```--help``` flag. eg:-

```bash
ecsopera --help
Usage: ecsopera [OPTIONS] COMMAND [ARGS]...

Options:
  --awsaccesskey TEXT
  --awssecretkey TEXT
  --awsregion TEXT
  --debug              Debug mode for true verbose output.
  --help               Show this message and exit.

Commands:
  aws-ecs-amiupdate  Use this command to update the container instance Amazon
                     Machine Image.
  aws-ecs-deploy     Use this command to deploy a new task definition to a
                     specified ECS service.
```

eg:-

```bash
ecsopera aws-ecs-amiupdate --help
Usage: ecsopera aws-ecs-amiupdate [OPTIONS]

Options:
  --ami TEXT        The AMI image to ++ to.
  --cluster TEXT    The ECS cluster name to operate on.
  --launchcfg TEXT  The Launch Configuration name to operate on.
  --help            Show this message and exit.
```
