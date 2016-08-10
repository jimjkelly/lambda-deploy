# Lambda Deploy - Easily Deploy Code to AWS Lambda

_Note: 0.1.0 introduces a change in how Lambda
Deploy operates - no longer are all directories
in the current working directory assumed to be
Lambdas, instead the current directory itself
is assumed to be a Lambda, and you need to call
it multiple times to upload multiple Lambdas._

This tool provides an easy way to deploy your code
to AWS's Lambda service. It provides a number of
useful features:

- Uses the standard boto/aws configuration options
- Handles packaging of (pure python) dependencies
- Allows for providing environment variables to Lambda
- Simplifies deployment steps

It should be noted that this is alpha, and issues
are expected, as well as changes to the interface.
Where an issue is known, I try and document it here,
but if you find something, please open an issue.

## Usage

At its heart the tool simply takes the directory
it is run from, and will package it up, giving it
the name of the directory, and pushing
it to AWS with the options you configure (see
[Configuration](#configuration) below).

While the tool is oriented towards Python at the
moment, there is no reason it could not push
other types of code to AWS, and its dependency
bundling could be extended to support other
languages. If this interests you, please open
a ticket.

A simple example usage would be the following:

	$ lambda-deploy deploy

This will load all the contents of the current
working directory into a Lambda and upload it
to AWS.

There is one other command aside from `deploy`:
`list`. You can guess what `list` does - it
lists your current Lambdas along with some
information about them.

At its most basic that's it. The next section
will cover how to configure things.

##  <a name="configuration"></a>Configuration

Configuration of the tool can be done though two
primary avenues - command line arguments and
environment variables. Within environment
variables, you can either set them yourself
using traditional means, or make use of a `.env`
file, which the tool will read in to populate
the environment.

Command line arguments will override
environment variables.

### AWS Credentials

You can configure AWS in any way which
[boto3](http://boto3.readthedocs.org/en/latest/guide/configuration.html)
supports. This tool actually does not touch
these at all, and relies on boto to pick
them up entirely. There's no way to pass
them via the command line.

### Lambda Options

There are several options can be passed in to 
your Lambda jobs, as well as one required
piece of information. Options that can also
be configured via an environment variable
will have the environment variable in
paranthesis in the header.

These correspond to boto3 arguments, so if
something is unclear, I recommend checking
the [boto3 documentation](http://boto3.readthedocs.org/en/latest/reference/services/lambda.html).

#### Role (LAMBDA_ROLE)

The only thing that is required is that you
specify the ARN role that your Lambda job
will operate under when communicating with
AWS. This can be specified via the
`-r/--role` option on the command line,
or via the environment variable. You must
configure via one of these methods, and
if you've done both, the command line
takes precedence.

#### Runtime (LAMBDA_RUNTIME)

This is the runtime on AWS Lambda that your
code will run under. It defaults to `python2.7`,
and can only be changed via the environment
variable.

#### Handler (LAMBDA_HANDLER)

This controls the entry point of your Lambda
code. It defaults to `lambda_function.lambda_handler`,
and can only be changed via the environment
variable.

This means, for example, that inside your
Lambda directory you would have a file
`lambda_function.py` which contains a
function `lambda_handler`.

#### Name (LAMBDA_NAME)

This is the name attached to your Lambda job
on AWS. It defaults to the directory name the
code resides in.  This can be specified via
the `-n/--name` option on the command line
or the environment variable.

#### Description (LAMBDA_DESCRIPTION)

This is the description attached to your Lambda
job on AWS. It defaults to "Lambda code for "
followed by the name of your Lambda job,
and can only be changed via the environment
variable.

#### Timeout (LAMBDA_TIMEOUT)

This is the amount of time, as an integer,
that Lambda should allow your job to run
before it is killed. This value defaults
to 3 seconds, and can only be changed via
the environment variable. The maximum that
AWS allows is 300 seconds.

#### Memory Size (LAMBDA\_MEMORY_SIZE)

The amount of memory, expressed as an integer
number of megabytes, that should be allocated
to your job. The default is 128, and values must
be given as multiples of 64, and can only be
changed via the environment variable. 

The amount of CPU is also inferred based on
this. For specifics, as well as maximums, I
recommend you check the AWS documentation.

### Tool Options

The following options can be provided to tweak
how the tool runs. Options that can also
be configured via an environment variable
will have the environment variable in
paranthesis in the header.

#### Environment File (LAMBDA\_ENV_FILE)

You can specify a different environment file
(from the default `.env`) to populate the
environment:

	$ lambda-deploy -e /my/env/file deploy

Note that shell expansions haven't been tested
here yet.

Note that a `.env` file inside your Lambda
directory will *not* be uploaded, to protect
you from accidentally uploading sensitive
information.  Use `LAMBDA_ENV_VARS` as is
described below.

#### Environment Variables (LAMBDA\_ENV_VARS)

You can specify one or more environment
variables to pluck out of the environment
the tool is running in, which will be placed in
a `.env` file that will be shipped with your
Lambdas.

	$ lambda-deploy -E MY_ENV_VAR -E MY_OTHER_ENV_VAR deploy

When setting this in an environment variable
itself, you can set values in a comma-delimated
fashion:

	LAMBDA_ENV_VARS=MY_ENV_VAR,MY_OTHER_ENV_VAR

This is useful for keeping all your configuration
inside a `.env` file. If for example `MY_ENV_VAR`
had a value of "foo" and `MY_OTHER_ENV_VAR` had
a value of bar, providing this options above would
result in a `.env` file being creatd in your LAMBDA
that looks like the following:

	MY_ENV_VAR=foo
	MY_OTHER_ENV_VAR=bar

#### Lambda Directory (LAMBDA_DIRECTORY)

By default the tool uses the current working
directory as its base to package, but you
can change this by providing this option:

	$ lambda-deploy -d /another/directory

Like the environment file, support for things
like shell expansions isn't really there yet.

#### Logging Level (LAMBDA\_LOGGING_LEVEL)

In order to change the logging level, you can
simply provide the `-v/--verbose` option to
get DEBUG level logging, or you can specify
what you want using the `-l/--logging-level`
option:

	$ lambda-deploy -l WARNING deploy

These correspond to standard Python logging
module levels - `CRITICAL`, `ERROR`, `WARNING`,
`INFO`, `DEBUG` or `NOTSET`.

## Automatic Dependency Bundling

One of the nicest features of this tool is
that you can use a `requirements.txt` file as
you normally would, and have those dependencies
bundles at the time you build your Lambda,
without polluting your local development
environment or even requiring a virtual
environment.

Just place the `requirements.txt` in the root
of your Lambda's folder (i.e. peered with
your Lambda handler file) and we'll handle the
rest.

If this sounds to good to be true, it is, or
at least there are some limits. Unfortunately,
while this works well for pure Python modules,
modules with compiled resources will not work
directly.

There are some ways around this. If you build
modules on an Amazon Linux x86_64 EC2 instance,
as long as the resulting code is relatively
self contained (i.e. doesn't require the
installation of compiled binaries elsewhere
on the system) then you should be able to move
this off of that system into your Lambda bundle.

Additionally, if you Google you can find some
people that have made special pip installable
versions of packages designed to work on
Lambda.

Feel free to open an issue if you have problems
getting this to work.

## An Example of Deploying Multiple Lambdas

A common use case is having a stable of Lambdas
that you would like deployed, perhaps as part of
a CI solution. An example of this might be
having a single git repo, in which you have a
directory called "lambdas" which contains
directories containing your individual Lambda
directories, like so:

	$ ls lambdas/
	lambdaA lambdaB

Assuming your CI solution inserts the current
git commit SHA1 in an environment variable, lets
call it `GIT_COMMIT_SHA1`, you could construct
a command like the following to only release
the Lambdas that changed:

	$ git show --pretty="format:" --name-only $GIT_COMMIT_SHA1 | grep '^lambdas' | cut -d/ -f 1-2 | uniq | xargs -I {} sh -c 'test -d "{}" && lambda-deploy -d "{}" deploy'

This correctly deals with not acting on things
outside of your lambdas directory, and only
uploading a Lambda if it changed. It does not
remove existing Lambdas if they are removed
from your git source - that's still something
you'd need to do manually.

## Development and Support

Pull requests and issues are welcome - join us on
[GitHub](https://github.com/jimjkelly/lambda-deploy)
