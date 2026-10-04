import json

def lambda_handler(event, context):
    state = (event.get("queryStringParameters") or {}).get("state", "FL").upper()
    if len(state) != 2 or not state.isalpha():
        return {"statusCode": 400, "body": json.dumps({"error": "invalid state"})}

    # Production: parameterized SQL + Secrets Manager/IAM auth + RDS Proxy.
    return {"statusCode": 200, "body": json.dumps({"state": state})}
