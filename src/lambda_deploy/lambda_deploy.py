"""
This handles packaging and deployment of lambdas
"""

import os
import io
import sys
import pip
import json
import yaep
import boto3
import zipfile
import logging
import optparse
from .utils import TemporaryDirectory
from .version import __version__


logger = logging.getLogger('lambda_deploy')


class ArgumentsError(Exception):
    pass


class LambdaDeploy(object):
    DEFAULT_ENV_FILE = '.env'
    DEFAULT_LAMBDA_DIR = os.getcwd()
    ACTIONS = ['deploy', 'list']

    def __init__(self, lambda_dir=None, env_file=None, env_vars=None,
                 role=None):

        if not env_file or env_file == self.DEFAULT_ENV_FILE:
            env_file = os.getenv('LAMBDA_ENV_FILE', '.env')

        yaep.populate_env(env_file)

        if not lambda_dir or lambda_dir == self.DEFAULT_LAMBDA_DIR:
            lambda_dir = yaep.env('LAMBDA_DIRECTORY', self.DEFAULT_LAMBDA_DIR)

        if not env_vars:
            # If there were no env_vars passed, look for them
            # in the ENV_VARS environment variable, and return
            # an empty list if they aren't there.
            env_vars = map(
                lambda x: x.strip(),
                filter(
                    None,
                    yaep.env('LAMBDA_ENV_VARS', '').split(',')
                )
            )

        self.env_vars = env_vars
        self.lambda_dir = lambda_dir
        self.client = boto3.client('lambda')
        self.role = role if role else yaep.env('LAMBDA_ROLE')

    def add_directory_to_zip(self, directory, zf):
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if not filename.endswith('.pyc'):
                    zf.write(
                        os.path.join(root, filename),
                        os.path.join(
                            root.replace(directory, ''),
                            filename
                        )
                    )

    def get_functions(self):
        return self.client.list_functions().get('Functions', [])

    def get_function_names(self):
        return [l.get('FunctionName') for l in self.get_functions()]

    def package(self, name):
        """Packages lambda data for deployment into a zip"""
        logger.info('Packaging lambda {}'.format(name))
        src_dir = os.path.join(self.lambda_dir, name)
        zfh = io.BytesIO()

        with zipfile.ZipFile(zfh, 'w') as zf:
            self.add_directory_to_zip(src_dir, zf)

            # Construct a .env file in the archive with our
            # needed envrionment variables.
            envinfo = zipfile.ZipInfo('.env')
            envinfo.external_attr = 0644 << 16L
            zf.writestr(
                envinfo,
                '\n'.join(
                    '{} = {}'.format(key, yaep.env(key))
                    for key in self.env_vars
                )
            )

            if 'requirements.txt' in os.listdir(src_dir):
                with TemporaryDirectory() as temp_dir:
                    pip_args = [
                        'install',
                        '-r',
                        os.path.join(src_dir, 'requirements.txt'),
                        '-t',
                        temp_dir,
                    ]

                    # Do pip install to temporary dir
                    pip.main(pip_args)

                    self.add_directory_to_zip(temp_dir, zf)

        zfh.seek(0)

        return zfh

    def deploy(self, *lambdas):
        """Deploys lambdas to AWS"""

        if not self.role:
            raise ArgumentsError('Role required')

        lambda_dirs = [
            l for l in os.listdir(self.lambda_dir)
            if not lambdas or l in lambdas
        ]

        for missing in [m for m in lambdas if m not in lambda_dirs]:
            logger.warn('Lambda {} not found, skipping.'.format(missing))

        for lambda_name in lambda_dirs:
            logger.debug('Deploying lambda {}'.format(lambda_name))
            zfh = self.package(lambda_name)

            if lambda_name in self.get_function_names():
                logger.info('Updating {} lambda'.format(lambda_name))

                response = self.client.update_function_code(
                    FunctionName=lambda_name,
                    ZipFile=zfh.getvalue(),
                    Publish=True
                )
            else:
                logger.info('Adding new {} lambda'.format(lambda_name))

                response = self.client.create_function(
                    FunctionName=lambda_name,
                    Runtime=yaep.env(
                        'LAMBDA_RUNTIME',
                        'python2.7'
                    ),
                    Role=self.role,
                    Handler=yaep.env(
                        'LAMBDA_HANDLER',
                        'lambda_function.lambda_handler'
                    ),
                    Code={
                        'ZipFile': zfh.getvalue(),
                    },
                    Description=yaep.env(
                        'LAMBDA_DESCRIPTION',
                        'Lambda code for {}'.format(lambda_name)
                    ),
                    Timeout=yaep.env(
                        'LAMBDA_TIMEOUT',
                        3,
                        convert_booleans=False,
                        type_class=int
                    ),
                    MemorySize=yaep.env(
                        'LAMBDA_MEMORY_SIZE',
                        128,
                        convert_booleans=False,
                        type_class=int
                    ),
                    Publish=True
                )

            status_code = response.get(
                'ResponseMetadata', {}
            ).get('HTTPStatusCode')

            if status_code in [200, 201]:
                logger.info('Successfully deployed {} version {}'.format(
                    lambda_name,
                    response.get('Version', 'Unkown')
                ))
            else:
                logger.error('Error deploying {}: {}'.format(
                    lambda_name,
                    response
                ))

    def list(self):
        """Lists already deployed lambdas"""
        for function in self.client.list_functions().get('Functions', []):
            lines = json.dumps(function, indent=4, sort_keys=True).split('\n')
            for line in lines:
                logger.info(line)


def print_usage(parser):
    parser.print_help()
    print ''  # Add line break
    sys.exit(1)


def main():
    usage = (
        'usage: %prog [options] action [args]\n\n'
        'Action is one of the following:\n'
    )

    for action in LambdaDeploy.ACTIONS:
        usage += '\n\t{:25}{}'.format(
            action + ':',
            getattr(LambdaDeploy, action).__doc__
        )

    parser = optparse.OptionParser(usage=usage)

    parser.add_option(
        '-d', '--directory', dest='directory',
        help=(
            'directory to look for lambdas in. Can be configured via '
            'environment variable LAMBDA_DIRECTORY as well.'
        )
    )

    parser.add_option(
        '-e', '--env-file', dest='env_file', default='.env',
        help=(
            'load environment variables from this file. They '
            'should be given as VARIABLE = VALUE, one per line. '
            'Defaults to .env. Can be configured via environment '
            'variable LAMBDA_ENV_FILE as well.'
        )
    )

    parser.add_option(
        '-E', '--environment-variable', dest='env_vars', action='append',
        help=(
            'load this environment variable into a .env file to be '
            'provided to your lambda jobs. Can be loaded easily using a '
            'library like Yaep. Can be provided multiple times to copy '
            'multiple environment variables. Can be configured via '
            'environment variable LAMBDA_ENV_VARS as well.'
        )
    )

    parser.add_option(
        '-r', '--role', dest='role',
        help=(
            'The ARN role that your Lambda job should assume when '
            'accessing other AWS services. This is required. Can '
            'be configured via environment variable LAMBDA_ROLE '
            'as well.'
        )
    )

    parser.add_option(
        '-l', '--logging-level', dest='logging_level', default='INFO',
        help=(
            'The specific logging level to use. These correspond to '
            'standard Python logging module levels - CRITICAL, ERROR, '
            'WARNING, INFO, DEBUG or NOTSET. Note that you can just '
            'use the -v/--verbose option as shorthand for -l DEBUG. '
            'If both are given, this takes precedence. Can be set via '
            'the LAMBDA_LOGGING_LEVEL environment variable.'
        )
    )

    parser.add_option(
        '-v', '--verbose', dest='verbose', action='store_true', default=False,
        help='enable verbose logging'
    )

    parser.add_option(
        '-V', '--version', dest='version', action='store_true', default=False,
        help='display version information and exit'
    )

    (options, args) = parser.parse_args()

    if options.version:
        print 'Version: ' + __version__
        sys.exit(0)

    if os.getenv('LAMBDA_LOGGING_LEVEL'):
        log_level = getattr(logging, os.getenv('LAMBDA_LOGGING_LEVEL'))
    elif options.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(
        name=__name__,
        level=log_level,
        format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.debug('Setting loglevel to DEBUG')

    action = args[0] if args else ''
    method = getattr(LambdaDeploy(
        lambda_dir=options.directory,
        env_file=options.env_file,
        env_vars=options.env_vars,
        role=options.role
    ), action, None)

    if not method:
        if action:
            logger.error('Action "{}" unknown - quitting.\n'.format(action))
        print_usage(parser)
    else:
        try:
            if args[1:]:
                method(*args[1:])
            else:
                method()
        except (TypeError, ArgumentsError):
            logger.error('Invalid arguments.')
            print_usage(parser)
