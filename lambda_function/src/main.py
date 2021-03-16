import os
import boto3

from base import LambdaFunctionBase


class CWScheduledEventManageRdsState(LambdaFunctionBase):
    """
    Class changing RDS instance states with a specific tag.
    """

    # Section specific to the lambda.
    ACTION = os.environ['PARAM_ACTION']
    RESOURCE_TAG_KEY = os.environ['PARAM_RESOURCE_TAG_KEY']
    RESOURCE_TAG_VALUE = os.environ['PARAM_RESOURCE_TAG_VALUE']
    AWS_REGIONS = os.environ['PARAM_AWS_REGIONS'].split(',')

    def _get_resource_identifiers_by_tag(self, aws_region_name, aws_resource_type, tag_key, tag_value):
        """ Returns all resources identifiers linked to tag. """
        resource_groups_tagging_api_client = boto3.client("resourcegroupstaggingapi", region_name=aws_region_name)
        resource_pages = resource_groups_tagging_api_client.get_paginator('get_resources').paginate(
            TagFilters=[
                {
                    'Key': tag_key,
                    'Values': [
                        tag_value,
                    ]
                },
            ],
            ResourceTypeFilters=[
                aws_resource_type
            ]
        )

        resource_identifiers = []

        for resource_page in resource_pages:
            for resource in resource_page['ResourceTagMappingList']:
                resource_identifier = resource['ResourceARN'].split(':')[-1]
                resource_identifiers.append(resource_identifier)

        return resource_identifiers

    def _stop_database_instances(self, aws_region_name, rds_database_instance_names):
        """ Stop Database instances. """
        rds_client = boto3.client('rds', region_name=aws_region_name)

        self.logger.info('> Stopping RDS database instances.')
        for rds_database_instance_name in rds_database_instance_names:
            self.logger.info('>> Stopping RDS database instance %s.', rds_database_instance_name)
            try:
                rds_client.stop_db_instance(DBInstanceIdentifier=rds_database_instance_name)
                self.logger.info('>> RDS database instance %s => [STOPPED].', rds_database_instance_name)
            except rds_client.exceptions.InvalidDBInstanceStateFault:
                self.logger.warning('>> Unable to stop RDS database instance %s due to invalid state.', rds_database_instance_name)

    def _start_database_instances(self, aws_region_name, rds_database_instance_names):
        """ Start Database instances. """
        rds_client = boto3.client('rds', region_name=aws_region_name)

        self.logger.info('> Starting RDS database instances.')
        for rds_database_instance_name in rds_database_instance_names:
            self.logger.debug('>> Starting RDS database instance %s.', rds_database_instance_name)
            try:
                rds_client.start_db_instance(DBInstanceIdentifier=rds_database_instance_name)
                self.logger.info('>> RDS database instance %s => [AVAILABLE].', rds_database_instance_name)
            except rds_client.exceptions.InvalidDBInstanceStateFault:
                self.logger.warning('>> Unable to start RDS database instance %s due to invalid state.', rds_database_instance_name)

    def _stop_database_clusters(self, aws_region_name, rds_database_cluster_names):
        """ Stop Database clusters. """
        rds_client = boto3.client('rds', region_name=aws_region_name)

        self.logger.info('> Stopping RDS database clusters.')
        for rds_database_cluster_name in rds_database_cluster_names:
            self.logger.info('>> Stopping RDS database cluster %s.', rds_database_cluster_name)
            try:
                rds_client.stop_db_cluster(DBClusterIdentifier=rds_database_cluster_name)
                self.logger.info('>> RDS database cluster %s => [STOPPED].', rds_database_cluster_name)
            except rds_client.exceptions.InvalidDBClusterStateFault:
                self.logger.warning('>> Unable to stop RDS database cluster %s due to invalid state.', rds_database_cluster_name)

    def _start_database_clusters(self, aws_region_name, rds_database_cluster_names):
        """ Start Database clusters. """
        rds_client = boto3.client('rds', region_name=aws_region_name)

        self.logger.info('> Starting RDS database clusters.')
        for rds_database_cluster_name in rds_database_cluster_names:
            self.logger.debug('>> Starting RDS database cluster %s.', rds_database_cluster_name)
            try:
                rds_client.start_db_cluster(DBClusterIdentifier=rds_database_cluster_name)
                self.logger.info('>> RDS database cluster %s => [AVAILABLE].', rds_database_cluster_name)
            except rds_client.exceptions.InvalidDBClusterStateFault:
                self.logger.warning('>> Unable to start RDS database cluster %s due to invalid state.', rds_database_cluster_name)

    def _execute(self, event, context):  # pylint: disable=W0613
        """ Execute the method. """
        self.logger.info('Starting the operation.')

        for aws_region_name in self.AWS_REGIONS:
            self.logger.info('> Searching RDS databases in region %s having tag %s=%s.',
                             aws_region_name, self.RESOURCE_TAG_KEY, self.RESOURCE_TAG_VALUE)

            # Get RDS databases by tag.
            rds_database_instance_names = self._get_resource_identifiers_by_tag(
                aws_region_name, "rds:db", self.RESOURCE_TAG_KEY, self.RESOURCE_TAG_VALUE)
            self.logger.info('> Found %s RDS databases in region %s having tag %s=%s.',
                             str(len(rds_database_instance_names)), aws_region_name, self.RESOURCE_TAG_KEY, self.RESOURCE_TAG_VALUE)

            # Enable/Disable instances
            if len(rds_database_instance_names) > 0:
                if self.ACTION in ['enable', 'start']:
                    self._start_database_instances(aws_region_name, rds_database_instance_names)
                elif self.ACTION in ['disable', 'stop']:
                    self._stop_database_instances(aws_region_name, rds_database_instance_names)

            self.logger.info('> Searching RDS clusters in region %s having tag %s=%s.',
                             aws_region_name, self.RESOURCE_TAG_KEY, self.RESOURCE_TAG_VALUE)

            # Get RDS clusters by tag.
            rds_database_cluster_names = self._get_resource_identifiers_by_tag(
                aws_region_name, "rds:cluster", self.RESOURCE_TAG_KEY, self.RESOURCE_TAG_VALUE)
            self.logger.info('> Found %s RDS clusters in region %s having tag %s=%s.',
                             str(len(rds_database_cluster_names)), aws_region_name, self.RESOURCE_TAG_KEY, self.RESOURCE_TAG_VALUE)

            # Enable/Disable clusters
            if len(rds_database_cluster_names) > 0:
                if self.ACTION in ['enable', 'start']:
                    self._start_database_clusters(aws_region_name, rds_database_cluster_names)
                elif self.ACTION in ['disable', 'stop']:
                    self._stop_database_clusters(aws_region_name, rds_database_cluster_names)

        self.logger.info('Operation completed successfully.')

        return self._build_response_ok()


def lambda_handler(event, context):
    """ Function invoked by AWS. """
    return CWScheduledEventManageRdsState().process_event(event, context)
