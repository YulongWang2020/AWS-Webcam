import json
import boto3
import datetime



def addVisitor(data):
    dynamodb = boto3.client('dynamodb')
    item = {
        "FaceId":{"S":data['faceid']},
        "name":{"S":data['name']},
        "phoneNumber": {"S": "+1"+data['phone']},
        "photo":{"L":[{
            "M":{
                "bucket":{"S":"visitor-photo-aws"},
                "address":{"S": str(data["image"])},
                "timestamp":{"S":str(datetime.datetime.now())}
            }}]
        }
    }
    response = dynamodb.put_item(
                    TableName = "visitors",
                    Item = item
                )
    return "successed"
def lambda_handler(event, context):
    data = event["messages"][0]["unstructured"]
    if "faceid" not in data.keys():
        return {
            'statusCode': 200,
            'message': "Error: Url missing faceid"
        }
    if (data["name"]) and (data["phone"]):
        if data["phone"].isalnum():
            if len(data["phone"]) == 10:
                message = addVisitor(data)
            else:
                message = "Please enter a 10-digit number"
        else:
            message = "Phone number needs to be a 10-digit number"
    else:
        message = "Both name and phone are required."
    
    
    return {
        'statusCode': 200,
        'message': message
    }
