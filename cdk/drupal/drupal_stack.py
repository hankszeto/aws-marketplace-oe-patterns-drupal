import json
from aws_cdk import (
    aws_autoscaling,
    aws_codedeploy,
    aws_codepipeline,
    aws_codepipeline_actions,
    aws_ec2,
    aws_efs,
    aws_elasticloadbalancingv2,
    aws_iam,
    aws_logs,
    aws_rds,
    aws_s3,
    aws_secretsmanager,
    aws_sns,
    core
)

AMI="ami-0a3f10562bb95d4b9"
TWO_YEARS_IN_DAYS=731

class DrupalStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        source_artifact_s3_bucket_name_param = core.CfnParameter(
            self,
            "SourceArtifactS3BucketName",
            default="github-user-and-bucket-githubartifactbucket-1c9jk3sjkqv8p"
        )
        source_artifact_s3_bucket_name_param = core.CfnParameter(
            self,
            "SourceArtifactS3Path",
            default="aws-marketplace-oe-patterns-drupal-example-site/refs/heads/develop.tar.gz"
        )

        certificate_arn_param = core.CfnParameter(
            self,
            "CertificateArn",
            default=""
        )
        certificate_arn_exists_condition = core.CfnCondition(
            self,
            "CertificateArnExists",
            expression=core.Fn.condition_not(core.Fn.condition_equals(certificate_arn_param.value, ""))
        )
        certificate_arn_does_not_exist_condition = core.CfnCondition(
            self,
            "CertificateArnNotExists",
            expression=core.Fn.condition_equals(certificate_arn_param.value, "")
        )
        vpc = aws_ec2.Vpc(
            self,
            "vpc",
            cidr="10.0.0.0/16"
        )
        secret = aws_secretsmanager.Secret(
            self,
            "secret",
            generate_secret_string=aws_secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"username":"user"}),
                generate_string_key="password"
            )
        )
        db_subnet_group = aws_rds.CfnDBSubnetGroup(
            self,
            "DBSubnetGroup",
            db_subnet_group_description="test",
            subnet_ids=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE).subnet_ids
        )
        db_cluster_parameter_group = aws_rds.CfnDBClusterParameterGroup(
            self,
            "DBClusterParameterGroup",
            description="test",
            family="aurora5.6",
            parameters={
                "character_set_client": "utf8",
                "character_set_connection": "utf8",
                "character_set_database": "utf8",
                "character_set_filesystem": "utf8",
                "character_set_results": "utf8",
                "character_set_server": "utf8",
                "collation_connection": "utf8_general_ci",
                "collation_server": "utf8_general_ci"
            }
        )
        db_cluster = aws_rds.CfnDBCluster(
            self,
            "DBCluster",
            engine="aurora",
            db_cluster_parameter_group_name=db_cluster_parameter_group.ref,
            db_subnet_group_name=db_subnet_group.ref,
            engine_mode="serverless",
            master_username="dbadmin",
            # TODO: get this working
            # https://docs.aws.amazon.com/cdk/latest/guide/get_secrets_manager_value.html
            # master_user_password=core.SecretValue.cfnDynamicReference(secret),
            master_user_password="dbpassword",
            scaling_configuration={
                "auto_pause": True,
                "min_capacity": 1,
                "max_capacity": 2,
                "seconds_until_auto_pause": 30
            },
            storage_encrypted=True
        )

        alb_sg = aws_ec2.SecurityGroup(
            self,
            "AlbSg",
            vpc=vpc
        )
        alb = aws_elasticloadbalancingv2.ApplicationLoadBalancer(
            self,
            "AppAlb",
            internet_facing=True,
            security_group=alb_sg,
            vpc=vpc
        )
        # if there is no cert...
        http_target_group = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            "AsgHttpTargetGroup",
            target_type=aws_elasticloadbalancingv2.TargetType.INSTANCE,
            port=80,
            vpc=vpc
        )
        http_target_group.node.default_child.cfn_options.condition = certificate_arn_does_not_exist_condition
        http_listener = aws_elasticloadbalancingv2.ApplicationListener(
            self,
            "HttpListener",
            default_target_groups=[http_target_group],
            load_balancer=alb,
            open=True,
            port=80
        )
        http_listener.node.default_child.cfn_options.condition = certificate_arn_does_not_exist_condition

        # if there is a cert...
        http_redirect_listener = aws_elasticloadbalancingv2.ApplicationListener(
            self,
            "HttpRedirectListener",
            load_balancer=alb,
            open=True,
            port=80
        )
        http_redirect_listener.add_redirect_response(
            "HttpRedirectResponse",
            host="#{host}",
            path="/#{path}",
            port="443",
            protocol="HTTPS",
            query="#{query}",
            status_code="HTTP_301"
        )
        http_redirect_listener.node.default_child.cfn_options.condition = certificate_arn_exists_condition
        https_target_group = aws_elasticloadbalancingv2.ApplicationTargetGroup(
            self,
            "AsgHttpsTargetGroup",
            target_type=aws_elasticloadbalancingv2.TargetType.INSTANCE,
            port=443,
            vpc=vpc
        )
        https_target_group.node.default_child.cfn_options.condition = certificate_arn_exists_condition
        https_listener = aws_elasticloadbalancingv2.ApplicationListener(
            self,
            "HttpsListener",
            certificates=[aws_elasticloadbalancingv2.ListenerCertificate(certificate_arn_param.value_as_string)],
            default_target_groups=[https_target_group],
            load_balancer=alb,
            open=True,
            port=443
        )
        https_listener.node.default_child.cfn_options.condition = certificate_arn_exists_condition

        notification_topic = aws_sns.Topic(
            self,
            "NotificationTopic"
        )
        system_log_group = aws_logs.CfnLogGroup(
            self,
            "DrupalSystemLogGroup",
            retention_in_days=TWO_YEARS_IN_DAYS
        )
        system_log_group.cfn_options.update_replace_policy = core.CfnDeletionPolicy.RETAIN
        system_log_group.cfn_options.deletion_policy = core.CfnDeletionPolicy.RETAIN
        access_log_group = aws_logs.CfnLogGroup(
            self,
            "DrupalAccessLogGroup",
            retention_in_days=TWO_YEARS_IN_DAYS
        )
        access_log_group.cfn_options.update_replace_policy = core.CfnDeletionPolicy.RETAIN
        access_log_group.cfn_options.deletion_policy = core.CfnDeletionPolicy.RETAIN
        error_log_group = aws_logs.CfnLogGroup(
            self,
            "DrupalErrorLogGroup",
            retention_in_days=TWO_YEARS_IN_DAYS
        )
        error_log_group.cfn_options.update_replace_policy = core.CfnDeletionPolicy.RETAIN
        error_log_group.cfn_options.deletion_policy = core.CfnDeletionPolicy.RETAIN
        app_instance_role = aws_iam.Role(
            self,
            "AppInstanceRole",
            assumed_by=aws_iam.ServicePrincipal('ec2.amazonaws.com'),
            inline_policies={
                "AllowStreamLogsToCloudWatch": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                'logs:CreateLogStream',
                                'logs:DescribeLogStreams',
                                'logs:PutLogEvents'
                            ],
                            resources=[
                                access_log_group.attr_arn,
                                error_log_group.attr_arn,
                                system_log_group.attr_arn
                            ]
                        )
                    ]
                ),
                "AllowStreamMetricsToCloudWatch": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                'ec2:DescribeVolumes',
                                'ec2:DescribeTags',
                                'cloudwatch:GetMetricStatistics',
                                'cloudwatch:ListMetrics',
                                'cloudwatch:PutMetricData'
                            ],
                            resources=['*']
                        )
                    ]
                )
            }
        )
        app_instance_role.add_managed_policy(aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'));
        sg = aws_ec2.SecurityGroup(
            self,
            "AppSg",
            vpc=vpc
        )
        instance_profile = aws_iam.CfnInstanceProfile(
            self,
            "AppInstanceProfile",
            roles=[app_instance_role.role_name]
        )
        launch_config = aws_autoscaling.CfnLaunchConfiguration(
            self,
            "AppLaunchConfig",
            image_id=AMI, # TODO: Put into CFN Mapping
            instance_type="t3.micro", # TODO: Parameterize
            iam_instance_profile=instance_profile.ref,
            security_groups=[sg.security_group_name],
            user_data=(
                core.Fn.base64(
                    core.Fn.sub(
                        """#!/bin/bash
cat <<EOF > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root",
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
  },
  "metrics": {
    "metrics_collected": {
      "collectd": {
        "metrics_aggregation_interval": 60
      },
      "disk": {
        "measurement": ["used_percent"],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      },
      "mem": {
        "measurement": ["mem_used_percent"],
        "metrics_collection_interval": 60
      }
    },
    "append_dimensions": {
      "ImageId": "\${!aws:ImageId}",
      "InstanceId": "\${!aws:InstanceId}",
      "InstanceType": "\${!aws:InstanceType}",
      "AutoScalingGroupName": "\${!aws:AutoScalingGroupName}"
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/dpkg.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/dpkg.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apt/history.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apt/history.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/cloud-init.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/cloud-init.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/cloud-init-output.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/cloud-init-output.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/auth.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/auth.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/syslog",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/syslog",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/amazon/ssm/amazon-ssm-agent.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/amazon/ssm/amazon-ssm-agent.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/amazon/ssm/errors.log",
            "log_group_name": "${DrupalSystemLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/amazon/ssm/errors.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apache2/access.log",
            "log_group_name": "${DrupalAccessLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apache2/access.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apache2/error.log",
            "log_group_name": "${DrupalErrorLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apache2/error.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apache2/access-ssl.log",
            "log_group_name": "${DrupalAccessLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apache2/access-ssl.log",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/apache2/error-ssl.log",
            "log_group_name": "${DrupalErrorLogGroup}",
            "log_stream_name": "{instance_id}-/var/log/apache2/error-ssl.log",
            "timezone": "UTC"
          }
        ]
      }
    },
    "log_stream_name": "{instance_id}"
  }
}
EOF
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /etc/ssl/private/apache-selfsigned.key \
  -out /etc/ssl/certs/apache-selfsigned.crt \
  -subj '/CN=localhost'
systemctl enable apache2 && systemctl start apache2
"""
                    )
                )
            )
        )
        asg = aws_autoscaling.CfnAutoScalingGroup(
            self,
            "AppAsg",
            launch_configuration_name=launch_config.ref,
            max_size="1",
            min_size="1",
            vpc_zone_identifier=vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE).subnet_ids
        )
        # https://github.com/aws/aws-cdk/issues/3615
        asg.add_override(
            "Properties.TargetGroupARNs",
            {
                "Fn::If": [
                    certificate_arn_exists_condition.logical_id,
                    [https_target_group.target_group_arn],
                    [http_target_group.target_group_arn]
                ]
            }
        )
        core.Tag.add(asg, "Name", "{}/AppAsg".format(self.stack_name))
        asg.add_override("UpdatePolicy.AutoScalingScheduledAction.IgnoreUnmodifiedGroupSizeProperties", True)

        sg_http_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AppSgHttpIngress",
            from_port=80,
            group_id=sg.security_group_id,
            ip_protocol="tcp",
            source_security_group_id=alb_sg.security_group_id,
            to_port=80
        )
        sg_http_ingress.cfn_options.condition = certificate_arn_does_not_exist_condition

        sg_https_ingress = aws_ec2.CfnSecurityGroupIngress(
            self,
            "AppSgHttpsIngress",
            from_port=443,
            group_id=sg.security_group_id,
            ip_protocol="tcp",
            source_security_group_id=alb_sg.security_group_id,
            to_port=443
        )
        sg_https_ingress.cfn_options.condition = certificate_arn_exists_condition

        # CICD Pipeline
        pipeline_role = aws_iam.Role(
            self,
            "PipelineRole",
            assumed_by=aws_iam.ServicePrincipal('codepipeline.amazonaws.com'),
            inline_policies={
                "CodePipelinePerms": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                'codedeploy:GetApplication',
                                'codedeploy:GetDeploymentGroup',
                                'codedeploy:ListApplications',
                                'codedeploy:ListDeploymentGroups',
                                'codepipeline:*',
                                'iam:ListRoles',
                                'iam:PassRole',
                                'lambda:GetFunctionConfiguration',
                                'lambda:ListFunctions',
                                's3:CreateBucket',
                                's3:GetBucketPolicy',
                                's3:GetObject',
                                's3:ListAllMyBuckets',
                                's3:ListBucket',
                                's3:PutBucketPolicy'
                            ],
                            resources=['*']
                        )
                    ]
                )
            }
        )

        source_bucket = aws_s3.Bucket.from_bucket_name(
            self,
            "SourceBucketByName",
            bucket_name="github-user-and-bucket-githubartifactbucket-1c9jk3sjkqv8p"
        )

        source_stage_role = aws_iam.Role(
            self,
            "SourceStageRole",
            assumed_by=aws_iam.ArnPrincipal(pipeline_role.role_arn),
            inline_policies={
                "SourceRolePerms": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                's3:*'
                            ],
                            resources=[
                                source_bucket.bucket_arn
                            ]
                        )
                    ]
                )
            }
        )

        source_output = aws_codepipeline.Artifact(artifact_name="DrupalBuild")

        code_deploy_role = aws_iam.Role(
            self,
            "CodeDeployRole",
            assumed_by=aws_iam.CompositePrincipal(
                aws_iam.ServicePrincipal('codedeploy.amazonaws.com'),
                aws_iam.ArnPrincipal(arn=pipeline_role.role_arn)
            ),
            inline_policies={
                "CodeDeployPerms": aws_iam.PolicyDocument(
                    statements=[
                        aws_iam.PolicyStatement(
                            effect=aws_iam.Effect.ALLOW,
                            actions=[
                                'autoscaling:*',
                                'codedeploy:*',
                                'ec2:*',
                                's3:*'
                            ],
                            resources=['*']
                        )
                    ]
                )
            }
        )

        code_deployment_application = aws_codedeploy.ServerApplication(
            self,
            "CodeDeploymentApplication",
            application_name="drupal"
        )

        # doesn't support cfn_asgs
        code_deployment_group = aws_codedeploy.ServerDeploymentGroup(
            self,
            "CodeDeploymentGroup",
            application=code_deployment_application,
            # auto_scaling_groups=[asg],
            deployment_group_name="{}-app".format(self.stack_name),
            deployment_config=aws_codedeploy.ServerDeploymentConfig.ALL_AT_ONCE,
            # TODO: get to work with either http or https
            load_balancer=aws_codedeploy.LoadBalancer.application(https_target_group),
            role=code_deploy_role
        )

        cicd_pipeline = aws_codepipeline.Pipeline(
            self,
            "AppPipeline",
            role=pipeline_role,
            stages=[
                aws_codepipeline.StageProps(
                    stage_name="Source",
                    actions=[
                        aws_codepipeline_actions.S3SourceAction(
                            bucket=source_bucket,
                            bucket_key="aws-marketplace-oe-patterns-drupal-example-site/refs/heads/develop.tar.gz",
                            action_name="SourceAction",
                            output=source_output,
                            role=source_stage_role,
                            run_order=1,
                            trigger=aws_codepipeline_actions.S3Trigger.POLL
                        ),
                    ]
                ),
                aws_codepipeline.StageProps(
                    stage_name="Deploy",
                    actions=[
                        # temp filler action since pipeline requires deploy stage
                        aws_codepipeline_actions.CodeDeployServerDeployAction(
                            action_name="DeployAction",
                            input=source_output,
                            deployment_group=code_deployment_group,
                            role=code_deploy_role,
                            run_order=1
                        )
                    ]
                )
            ]
        )

        # EFS
        efs_sg = aws_ec2.SecurityGroup(
            self,
            "EfsSg",
            description="EFS security group",
            security_group_name="sg_efs",
            vpc=vpc,
        )

        efs_sg.add_ingress_rule(
            peer=sg,
            connection=aws_ec2.Port.tcp(2049)
        )

        efs = aws_efs.EfsFileSystem(
            self,
            "AppEfs",
            security_group=efs_sg,
            vpc=vpc
        )
