bash:
	docker-compose run -w /code --rm drupal bash

bootstrap:
	docker-compose run -w /code/cdk --rm drupal cdk bootstrap aws://992593896645/us-east-1

build:
	docker-compose build

clean:
	docker-compose run -w /code --rm drupal bash ./cleanup.sh

clean-all-tcat:
	docker-compose run -w /code --rm drupal bash ./cleanup.sh all tcat

clean-buckets:
	docker-compose run -w /code --rm drupal bash ./cleanup.sh buckets

clean-buckets-tcat:
	docker-compose run -w /code --rm drupal bash ./cleanup.sh buckets tcat

clean-logs:
	docker-compose run -w /code --rm drupal bash ./cleanup.sh logs

clean-logs-tcat:
	docker-compose run -w /code --rm drupal bash ./cleanup.sh logs tcat

clean-snapshots:
	docker-compose run -w /code --rm drupal bash ./cleanup.sh snapshots

clean-snapshots-tcat:
	docker-compose run -w /code --rm drupal bash ./cleanup.sh snapshots tcat

deploy:
	docker-compose run -w /code/cdk --rm drupal cdk deploy \
	--require-approval never \
	--parameters CertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/77ba53df-8613-4620-8b45-3d22940059d4 \
	--parameters CloudFrontCertificateArn=arn:aws:acm:us-east-1:992593896645:certificate/77ba53df-8613-4620-8b45-3d22940059d4 \
	--parameters CloudFrontAliases=cdn-oe-patterns-drupal-${USER}.dev.patterns.ordinaryexperts.com \
	--parameters CloudFrontEnable=true \
	--parameters CustomerVpcId=vpc-00425deda4c835455 \
	--parameters CustomerVpcPrivateSubnet1=subnet-030c94b9795c6cb96 \
	--parameters CustomerVpcPrivateSubnet2=subnet-079290412ce63c4d5 \
	--parameters CustomerVpcPublicSubnet1=subnet-0c2f5d4daa1792c8d \
	--parameters CustomerVpcPublicSubnet2=subnet-060c39a6ded9e89d7 \
	--parameters DBSnapshotIdentifier=arn:aws:rds:us-east-1:992593896645:cluster-snapshot:oe-patterns-drupal-default-20200519 \
	--parameters DnsHostname=oe-patterns-drupal-acarlton.dev.patterns.ordinaryexperts.com \
	--parameters ElastiCacheEnable=true \
	--parameters PipelineArtifactBucketName=github-user-and-bucket-taskcatbucket-2zppaw3wi3sx \
	--parameters SecretArn=arn:aws:secretsmanager:us-east-1:992593896645:secret:/test/drupal/secret-P6y46J \
	--parameters SourceArtifactS3ObjectKey=aws-marketplace-oe-patterns-drupal-example-site/refs/heads/feature/DP-42--cfn-elasticache-drupal-config.tar.gz

destroy:
	docker-compose run -w /code/cdk --rm drupal cdk destroy

diff:
	docker-compose run -w /code/cdk --rm drupal cdk diff

lint:
	docker-compose run -w /code --rm drupal bash -c "cd cdk \
	&& cdk synth > ../test/template.yaml \
	&& cd ../test \
	&& taskcat lint"

packer:
	docker-compose run -w /code/packer drupal packer build ami.json
.PHONY: packer

publish:
	docker-compose run -w /code --rm drupal bash -c "mkdir -p dist \
	&& cd cdk \
	&& cdk synth \
	--version-reporting false \
	--path-metadata false \
	--asset-metadata false > ../dist/template.yaml \
	&& cd .. \
	&& aws s3 cp dist/template.yaml \
	s3://deployment-user-and-buck-deploymentartifactbucket-17r9c9e9pu794/`git describe`/oe-drupal-patterns-template.yaml \
	--sse aws:kms --acl public-read"

rebuild:
	docker-compose build --no-cache

synth:
	docker-compose run -w /code/cdk --rm drupal cdk synth \
	--version-reporting false \
	--path-metadata false \
	--asset-metadata false

test:
	docker-compose run -w /code --rm drupal bash -c "cd cdk \
	&& cdk synth > ../test/template.yaml \
	&& cd ../test \
	&& taskcat test run"
.PHONY: test
