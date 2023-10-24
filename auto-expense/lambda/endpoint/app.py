import json
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: dict, context: dict) -> dict:
    parameters = json.loads(event["body"])
    image_url = parameters["image"]
    question = parameters.get("question", None)

    fixed_questions = False
    if not question:
        question = [
            "What is the total amount?",
            "What is the date?",
            "What is the name of the merchant?",
        ]
        fixed_questions = True
    else:
        question = [question]

    runtime = boto3.client("sagemaker-runtime")

    output = []
    for q in question:
        try:
            resp = runtime.invoke_endpoint(
                EndpointName="auto-expense-endpoint",
                ContentType="application/json",
                Body=json.dumps(
                    {
                        "inputs": {
                            "image": image_url,
                            "question": q,
                            "timeout": 300,
                        }
                    }
                ),
            )
        except (
            runtime.exceptions.ServiceUnavailable,
            runtime.exceptions.InternalFailure,
        ) as e:
            logger.exception("Sagemaker service is unavailable or failed.")
            return {
                "statusCode": e["ResponseMetadata"]["HTTPStatusCode"],
                "body": json.dumps(
                    {"error": "Service is unavailable. Please try again later"}
                ),
            }
        except (runtime.exceptions.ValidationError, runtime.exceptions.ModelError) as e:
            logger.exception(e.response["Error"]["Message"])
            return {
                "statusCode": e["ResponseMetadata"]["HTTPStatusCode"],
                "body": json.dumps(
                    {"Error": "Invalid input. Expected image and question parameters."}
                ),
            }
        except runtime.exceptions.ModelNotReadyException:
            logger.exception("Model is not ready.")
            return {
                "statusCode": 429,
                "body": json.dumps(
                    {"error": "Model is not ready. Please try again later."}
                ),
            }

        model_resp = json.loads(resp["Body"].read().decode())
        output.append(model_resp)

    if fixed_questions:
        print(output)
        return {
            "amount": output[0][0]["answer"],
            "date": output[1][0]["answer"],
            "merchant": output[2][0]["answer"],
        }

    return output[0]
