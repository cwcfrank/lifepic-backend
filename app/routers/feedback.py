"""
Feedback router for handling user problem reports with image uploads.
Uploads images to GCS and sends email notifications via SMTP.
"""
import os
import base64
import json
import uuid
import smtplib
from datetime import datetime, timedelta
from typing import Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from google.cloud import storage
from google.oauth2 import service_account

router = APIRouter(prefix="/api", tags=["feedback"])


def get_gcs_client():
    """Initialize GCS client with service account credentials from environment."""
    json_str = base64.b64decode(os.environ["GCS_SERVICE_ACCOUNT_JSON"]).decode()
    info = json.loads(json_str)
    credentials = service_account.Credentials.from_service_account_info(info)
    return storage.Client(credentials=credentials)


async def upload_to_gcs(file: UploadFile) -> str:
    """
    Upload a file to GCS and return a signed URL.

    Args:
        file: The uploaded file from the request.

    Returns:
        A signed URL valid for 7 days.
    """
    json_str = base64.b64decode(os.environ["GCS_SERVICE_ACCOUNT_JSON"]).decode()
    info = json.loads(json_str)
    credentials = service_account.Credentials.from_service_account_info(info)
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(os.environ["GCS_BUCKET_NAME"])

    # Generate unique filename with date prefix
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    blob_name = f"feedback-images/{date_prefix}/{uuid.uuid4()}.{ext}"

    blob = bucket.blob(blob_name)
    content = await file.read()
    blob.upload_from_string(content, content_type=file.content_type or "image/jpeg")

    # Generate signed URL valid for 7 days (for email viewing)
    signed_url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(days=7),
        method="GET",
        credentials=credentials,
    )

    return signed_url


def send_email(description: str, email: Optional[str], image_urls: List[str]):
    """
    Send feedback email with description and image links.
    
    Args:
        description: The problem description from the user.
        email: Optional user email for follow-up.
        image_urls: List of public URLs for uploaded images.
    """
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.environ["SMTP_PORT"])
    smtp_user = os.environ["SMTP_USERNAME"]
    smtp_pass = os.environ["SMTP_PASSWORD"]
    recipients = os.environ["SMTP_RECIPIENTS"].split(",")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "ParkRadar Feedback"
    msg["From"] = smtp_user  # Use plain email address for Zoho
    msg["To"] = ", ".join(recipients)

    # Build HTML email content with embedded images
    images_html = ""
    if image_urls:
        images_html = "<h3>附加圖片：</h3>" + "".join([
            f'<p><a href="{url}"><img src="{url}" style="max-width:400px; margin:10px 0;"/></a></p>'
            for url in image_urls
        ])

    html = f"""
    <html>
    <body>
        <h2>新的問題回報</h2>
        <p><strong>問題描述：</strong></p>
        <p>{description.replace(chr(10), '<br>')}</p>
        <br>
        <p><strong>用戶 Email：</strong> {email if email else '未提供'}</p>
        <p><strong>發送時間：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        {images_html}
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html"))

    # Use SSL for port 465, STARTTLS for port 587
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_string())


@router.post("/feedback")
async def submit_feedback(
    description: str = Form(...),
    email: Optional[str] = Form(None),
    images: List[UploadFile] = File(default=[])
):
    """
    Submit user feedback with optional image attachments.
    
    - **description**: Problem description (required)
    - **email**: User email for follow-up (optional)
    - **images**: Up to 3 image files, max 5MB each (optional)
    
    Returns success status and message.
    """
    try:
        # Validate description
        if not description.strip():
            raise HTTPException(status_code=400, detail="請輸入問題描述")
        
        # Validate image count
        if len(images) > 3:
            raise HTTPException(status_code=400, detail="最多只能上傳 3 張圖片")
        
        # Validate file sizes (5MB limit per image)
        for img in images:
            if img.filename:  # Only check if file was actually uploaded
                content = await img.read()
                await img.seek(0)  # Reset file pointer for later upload
                if len(content) > 5 * 1024 * 1024:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"圖片 {img.filename} 超過 5MB 限制"
                    )
        
        # Upload images to GCS
        image_urls = []
        for img in images:
            if img.filename:  # Only upload if file was actually provided
                url = await upload_to_gcs(img)
                image_urls.append(url)
        
        # Send email notification
        send_email(description, email, image_urls)
        
        return {"success": True, "message": "問題回報已發送"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Feedback Error] {e}")
        raise HTTPException(status_code=500, detail=str(e))
