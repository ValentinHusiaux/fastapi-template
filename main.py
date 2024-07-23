import os
from fastapi import FastAPI, File, UploadFile, HTTPException
import boto3
from botocore.exceptions import NoCredentialsError
from fastapi.responses import StreamingResponse

app = FastAPI()

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

@app.get("/ping")
async def ping():
    return "pong"

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        s3.upload_fileobj(file.file, os.getenv('AWS_S3_BUCKET_NAME'), file.filename)
        return {"filename": file.filename}
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="Credentials not available")

@app.get("/download/{filename}")
async def download_file(filename: str):
    try:
        file_obj = s3.get_object(Bucket=os.getenv('AWS_S3_BUCKET_NAME'), Key=filename)
        return StreamingResponse(file_obj['Body'], media_type='application/octet-stream')
    except NoCredentialsError:
        raise HTTPException(status_code=400, detail="Credentials not available")
    except s3.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="File not found")
