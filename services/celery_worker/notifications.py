import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import firebase_admin
from firebase_admin import credentials, messaging

# Инициализация SendGrid
sendgrid_client = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))

# Инициализация Firebase
cred = credentials.Certificate('path/to/firebase-adminsdk.json')
firebase_admin.initialize_app(cred)

def send_email(to_email, subject, content):
    message = Mail(
        from_email='your-email@example.com',
        to_emails=to_email,
        subject=subject,
        html_content=content)
    try:
        response = sendgrid_client.send(message)
        print(f"Email sent. Status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

def send_push_notification(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )
    try:
        response = messaging.send(message)
        print(f"Push notification sent. Response: {response}")
        return True
    except Exception as e:
        print(f"Error sending push notification: {str(e)}")
        return False
