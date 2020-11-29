import json
import base64
import boto3
import cv2
import uuid
from botocore.errorfactory import ClientError
import time
from random import randint
import datetime

def save_image(imageId):
    s3_client = boto3.client('s3')
    kinesis_client = boto3.client("kinesisvideo",region_name = "us-east-1")
    response = kinesis_client.get_data_endpoint(
        StreamARN = "arn:aws:kinesisvideo:us-east-1:043550019784:stream/helloworld/1605113960964",
        APIName = "GET_MEDIA")
    video_clinet = boto3.client("kinesis-video-media",endpoint_url = response["DataEndpoint"],region_name = "us-east-1")
    response = video_clinet.get_media(
        StreamARN = "arn:aws:kinesisvideo:us-east-1:043550019784:stream/helloworld/1605113960964",
        StartSelector = {"StartSelectorType" : "NOW"})
    print("video get")
    frame = response["Payload"].read(1024*1024)
    
    with open('/tmp/stream.avi', 'wb') as f:
                f.write(frame)
                print("writing complete")
                cap = cv2.VideoCapture('/tmp/stream.avi')
                print(cap)
                print("loading complete")
                
    # print("uploading video to s3")
    # s3_client.upload_file('/tmp/stream.avi', 'visitor-photo-aws', 'stream.avi')
    # print("video saved")
    
    success, image = cap.read()
    imagepath = "/tmp/"+imageId + '.jpg'
    cv2.imwrite(imagepath,image)
    #store image to s3
    response = s3_client.upload_file( imagepath, 'visitor-photo-aws', imageId +".jpg")
    print("saved")
    return image,imageId+".jpg"


def add_faces_to_collection(bucket,photo,collection_id):


    
    client=boto3.client('rekognition')

    response=client.index_faces(CollectionId=collection_id,
                                Image={'S3Object':{'Bucket':bucket,'Name':photo}},
                                ExternalImageId=photo,
                                MaxFaces=1,
                                QualityFilter="AUTO",
                                DetectionAttributes=['ALL'])

    print ('Results for ' + photo) 	
    print('Faces indexed:')						
    for faceRecord in response['FaceRecords']:
         print('  Face ID: ' + faceRecord['Face']['FaceId'])
         print('  Location: {}'.format(faceRecord['Face']['BoundingBox']))

    print('Faces not indexed:')
    for unindexedFace in response['UnindexedFaces']:
        print(' Location: {}'.format(unindexedFace['FaceDetail']['BoundingBox']))
        print(' Reasons:')
        for reason in unindexedFace['Reasons']:
            print('   ' + reason)
    return len(response['FaceRecords'])
def addface():
    imageid = str(uuid.uuid4())
    print("add face",)
    image, imageId = save_image(imageid)
    add_faces_to_collection("visitor-photo-aws",imageId,"myfacelist")
    print("Face_Added")
    return


def askforpermission(FaceId,ImageId):
    url = 'https://visitor-photo-aws.s3.amazonaws.com/owner.html' +"?" + "faceid=" +FaceId +"&image=https://visitor-photo-aws.s3.amazonaws.com/"+ImageId
    messages = "A new visitor detected: " + url
    sns = boto3.client("sns")
    sns.publish(
        PhoneNumber="+15132555810",
        Message=messages)
    print("message sent")

def sendOTP(dyresponse):
    
    
    
    
    faceId = dyresponse["Item"]["FaceId"]["S"]
    print("the faceId: "+faceId)
    phone = dyresponse["Item"]["phoneNumber"]["S"]
    dynamodb = boto3.client('dynamodb')
    dyresponse = dynamodb.get_item(
            TableName='passcodes',
            Key={
            'FaceId': {"S": faceId}
            }
        )
    if "Item" in dyresponse.keys():
        print("Code already sent")
        return
    # append new face
    imageid = str(uuid.uuid4())
    print("append new face to dynamodn",)
    image, imageId = save_image(imageid)
    key = {"FaceId":{"S":faceId}}
    updateitem = {
                        "M":{
                            "bucket":{"S":"visitor-photo-aws"},
                            "address":{"S": 'https://visitor-photo-aws.s3.amazonaws.com/' +imageId},
                            "timestamp":{"S":str(datetime.datetime.now())}
                    }}
    response = dynamodb.update_item(
        TableName='visitors',
        Key={
            'FaceId': {"S": faceId},
        },
        UpdateExpression="SET #ri = list_append(#ri, :vals)",
        ExpressionAttributeNames={"#ri": "photo"},
        ExpressionAttributeValues={":vals": {"L": [updateitem]}},
        ReturnValues="UPDATED_NEW"
    )
    
    
    sns = boto3.client("sns")
    url = 'https://visitor-photo-aws.s3.amazonaws.com/virtualdoor.html' +"?" + "faceid=" +faceId
    OTP = str(randint(100000,999999))
    messages = "This is your OTP: " + OTP +  ", please do not share with others. Please enter here: " + url
    sns.publish(
        PhoneNumber=phone,
        Message=messages)
    print("OTP sent")
    response = dynamodb.put_item(
                    TableName = "passcodes",
                    Item = {
                        "FaceId":{"S":faceId},
                        "expire":{"N":str(int(time.time()+300))},
                        "OTP":{"S": OTP}
                        }
                )
    print("OTP added in database")
    
    return

def lambda_handler(event, context):
    dynamodb = boto3.client('dynamodb')
    data_raw = event['Records'][0]['kinesis']['data']
    print(data_raw)
    data_str = base64.b64decode(data_raw).decode('ASCII')
    data = json.loads(data_str)
    print(data)
    if not data["FaceSearchResponse"]:
        print("No Face Detected")
        return {}
        
    if not data["FaceSearchResponse"][0]["MatchedFaces"]:
        print("adding Time marker")
        response = dynamodb.put_item(
                    TableName = "tempface",
                    Item = {
                        "FaceId":{"S":"TimeMarker"},
                        "expire":{"N":str(int(time.time()+10))}
                        }
                )
        addface()
        return {}
    
    dyresponse = dynamodb.get_item(
            TableName='tempface',
            Key={
            'FaceId': {"S": "TimeMarker"}
            }
        )
    if "Item" in dyresponse.keys():
        waitingtime = dyresponse["Item"]["expire"]["N"]
        print(waitingtime,time.time())
        if int(waitingtime) > int(time.time()):
            print("still waiting for timemarker")
            return{}
    
    print(len(data["FaceSearchResponse"][0]["MatchedFaces"]),"face matched")
    if len(data["FaceSearchResponse"][0]["MatchedFaces"]) > 1:
        for i in range(1,len(data["FaceSearchResponse"][0]["MatchedFaces"])):
            s3imageId = data["FaceSearchResponse"][0]["MatchedFaces"][i]["Face"]["ExternalImageId"]
            faceId = data["FaceSearchResponse"][0]["MatchedFaces"][i]["Face"]["FaceId"]
            s3 = boto3.client('s3') 
            response = s3.delete_object(Bucket="visitor-photo-aws", Key=s3imageId)
            rekognitionclient =boto3.client('rekognition')
            response = rekognitionclient.delete_faces(
                CollectionId='myfacelist',
                FaceIds=[faceId,])
            print("one facelist deleted")
            
        return {}
    faceId = data["FaceSearchResponse"][0]["MatchedFaces"][0]["Face"]["FaceId"]
    imageId = data["FaceSearchResponse"][0]["MatchedFaces"][0]["Face"]["ExternalImageId"]
    # save_image(imageId[0:-4])

    dyresponse = dynamodb.get_item(
        TableName='visitors',
        Key={
        'FaceId': {"S": faceId}
        }
    )
    print(dyresponse)
    print(dyresponse.keys())
    if "Item" in dyresponse.keys():
        print("Permission Proven")
        sendOTP(dyresponse)
    else:
        print("Permission Failed")
        # add index in database
        # Check if exist
        dyresponse = dynamodb.get_item(
            TableName='tempface',
            Key={
            'FaceId': {"S": faceId}
            }
        )
        if "Item" not in dyresponse.keys(): 
            print("New face, adding to tempface database and ask for permission")
            response = dynamodb.put_item(
                    TableName = "tempface",
                    Item = {
                        "FaceId":{"S":faceId},
                        "expire":{"N":str(int(time.time()+300))}
                        }
                )
            askforpermission(faceId,imageId)
        else:
            print("message have been sent in 5 mintues")
    
    return {}
