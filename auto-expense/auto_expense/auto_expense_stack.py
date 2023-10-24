from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as _lambda_python,
    aws_sagemaker_alpha as sagemaker_alpha,
    RemovalPolicy,
    CfnOutput,
    Duration,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    CfnParameter,
    CfnCondition,
    Fn,
)
from constructs import Construct

# ruff: noqa: F841

PRODUCTION_VARIANT = "AllTraffic"


class AutoExpenseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # define the lambda function invoked by the end user
        user_endpoint = _lambda_python.PythonFunction(
            self,
            "UserEndpoint",
            entry="lambda/endpoint",
            index="app.py",
            handler="lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(30),
        )
        url = user_endpoint.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
            cors={
                "allowed_origins": ["*"],
                "allowed_headers": ["*"],
            },
        )

        endpoint_url = CfnOutput(self, "UserEndpointURL", value=url.url)

        # Sagemaker pipeline

        # environment vars
        # The official HuggingFace container can automatically download the model
        # from the HuggingFace model hub if the HF_MODEL_ID environment variable is set.
        # https://huggingface.co/docs/sagemaker/inference#deploy-a-model-from-the-hub
        hf_container_env = {
            "HF_MODEL_ID": "impira/layoutlm-invoices",
            "HF_TASK": "document-question-answering",
        }

        container = sagemaker_alpha.ContainerDefinition(
            image=sagemaker_alpha.ContainerImage.from_asset(
                directory="docker",
                file="Dockerfile",
            ),
            environment=hf_container_env,
        )

        # define the model
        model_cpu = sagemaker_alpha.Model(
            self,
            "AutoExpenseModel",
            model_name="auto-expense-model-cpu",
            containers=[
                container,
            ],
        )

        # define the endpoint config
        endpoint_config = sagemaker_alpha.EndpointConfig(
            self,
            "AutoExpenseEndpointConfig",
            endpoint_config_name="auto-expense-endpoint-config",
            instance_production_variants=[
                sagemaker_alpha.InstanceProductionVariantProps(
                    model=model_cpu,
                    instance_type=sagemaker_alpha.InstanceType.M5_XLARGE,
                    initial_instance_count=1,
                    variant_name=PRODUCTION_VARIANT,
                )
            ],
        )

        # define the endpoint
        endpoint = sagemaker_alpha.Endpoint(
            self,
            "AutoExpenseEndpoint",
            endpoint_name="auto-expense-endpoint",
            endpoint_config=endpoint_config,
        )
        endpoint.grant_invoke(user_endpoint)

        # scaling
        prod_variant = endpoint.find_instance_production_variant(PRODUCTION_VARIANT)
        instance_count = prod_variant.auto_scale_instance_count(
            max_capacity=2,
            min_capacity=1,
        )
        instance_count.scale_on_invocations(
            "AutoExpenseScaling",
            max_requests_per_second=5,
            scale_in_cooldown=Duration.seconds(300),
            scale_out_cooldown=Duration.seconds(300),
        )

        deploy_test_website = self.node.try_get_context("deploy_test_website")

        if deploy_test_website:
            website_bucket = s3.Bucket(
                self,
                "WebsiteBucket",
                public_read_access=True,
                object_ownership=s3.ObjectOwnership.OBJECT_WRITER,
                enforce_ssl=True,
                block_public_access=s3.BlockPublicAccess(
                    block_public_acls=False,
                    block_public_policy=False,
                    ignore_public_acls=False,
                    restrict_public_buckets=False,
                ),
                removal_policy=RemovalPolicy.DESTROY,
                auto_delete_objects=True,
            )

            s3deploy.DeployTimeSubstitutedFile(
                self,
                "WebsiteIndex",
                destination_bucket=website_bucket,
                source="./website/index.html",
                substitutions={"FUNCTION_URL": url.url},
            )

            website_url = CfnOutput(
                self, "WebsiteURL", value=website_bucket.bucket_website_url
            )
