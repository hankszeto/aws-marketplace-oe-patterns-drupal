import setuptools


with open("README.md") as fp:
    long_description = fp.read()


CDK_VERSION="1.33.1"

setuptools.setup(
    name="drupal",
    version="0.0.1",

    description="An empty CDK Python app",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "drupal"},
    packages=setuptools.find_packages(where="drupal"),

    install_requires=[
        f"aws-cdk.core=={CDK_VERSION}",
        f"aws-cdk.aws-autoscaling=={CDK_VERSION}",
        f"aws-cdk.aws-ec2=={CDK_VERSION}",
        f"aws-cdk.aws-elasticloadbalancingv2=={CDK_VERSION}",
        f"aws-cdk.aws-iam=={CDK_VERSION}",
        f"aws-cdk.aws-rds=={CDK_VERSION}",
        f"aws-cdk.aws-secretsmanager=={CDK_VERSION}",
        f"aws-cdk.aws-sns=={CDK_VERSION}",
        f"aws-cdk.aws-s3=={CDK_VERSION}",
        f"aws-cdk.aws-codepipeline=={CDK_VERSION}",
        f"aws-cdk.aws-codepipeline-actions=={CDK_VERSION}"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
