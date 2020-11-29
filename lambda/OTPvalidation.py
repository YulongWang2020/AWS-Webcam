import json
import boto3

def lambda_handler(event, context):
    dynamodb = boto3.client('dynamodb')
    OTP = event["messages"][0]["unstructured"]["OTP"]
    faceId = event["messages"][0]["unstructured"]["faceid"]
    dyresponse = dynamodb.get_item(
        TableName='passcodes',
        Key={
        'FaceId': {"S": faceId}
        }
    )
    if "Item" in dyresponse.keys():
        print(dyresponse["Item"]["OTP"]["S"],OTP)
        if dyresponse["Item"]["OTP"]["S"] == str(OTP):
            return {"message" :"Correct, door opened"}

    return {"message" :"Incorrect OTP"}

    