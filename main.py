import os
import uuid
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Depends
import boto3
from botocore.exceptions import NoCredentialsError
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from pydantic import BaseModel

# Charger les variables d'environnement à partir du fichier .env
load_dotenv()

app = FastAPI()

# Initialiser le client S3
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

# Initialiser le client DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)
table_upload = dynamodb.Table('FileUpload')
table_download = dynamodb.Table('FileDownload')

@app.get("/ping")
async def ping():
    return "pong"

class UploadMetadata(BaseModel):
    description: str

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        s3.upload_fileobj(file.file, os.getenv('AWS_S3_BUCKET_NAME'), file.filename)
        
        table_upload.put_item(
            Item={
                'file_id': file_id,
                'filename': file.filename,
                'size': file.size,
                'upload_date': str(datetime.now()),
                'delete_date': None
            }
        )
        return {"filename": file.filename}
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="Credentials not available")

@app.get("/download/{filename}")
async def download_file(filename: str, request: Request):
    try:
        file_obj = s3.get_object(Bucket=os.getenv('AWS_S3_BUCKET_NAME'), Key=filename)
        
        table_download.put_item(
            Item={
                'download_id': str(uuid.uuid4()),
                'filename': filename,
                'download_date': str(datetime.now()),
                'ip_address': request.client.host
            }
        )
        return StreamingResponse(file_obj['Body'], media_type='application/octet-stream')
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="Credentials not available")
    except s3.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="File not found")

@app.delete("/delete/{filename}")
async def delete_file(filename: str):
    try:
        s3.delete_object(Bucket=os.getenv('AWS_S3_BUCKET_NAME'), Key=filename)
        
        response = table_upload.update_item(
            Key={'filename': filename},
            UpdateExpression="set delete_date = :d",
            ExpressionAttributeValues={':d': str(datetime.now())},
            ReturnValues="UPDATED_NEW"
        )
        return {"deleted": filename, "response": response}
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="Credentials not available")
    except s3.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/files")
async def list_files():
    try:
        response = table_upload.scan(
            FilterExpression="attribute_not_exists(delete_date)"
        )
        return {"files": response['Items']}
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="Credentials not available")
