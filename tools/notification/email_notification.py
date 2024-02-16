"""
Aim: Send email if any new trades are executed during the past 5 minutes.
In the email body, include the action taken, and the graph of the traded token.
"""

import smtplib
import base64
import os

import pandas as pd
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

from tools import color_functions as c
from tools.logging_formatter import logger
from tools.resources import EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT, SENDER_EMAIL


def df_to_html(df: pd.DataFrame):
    return df.to_html(index=False, justify='left')


# noinspection PyShadowingNames
def send_email(receiver_email_list, subject, body, tables=None, table_titles=None, images_paths=None):
    if tables is None:
        tables = []
    if images_paths is None:
        images_paths = []
    if table_titles is None:
        table_titles = []

    # Use SMTP to send emails
    try:
        logger.info(f"{c.GREEN}Starting to send email.{c.RESET}")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)

        for receiver_email in receiver_email_list:
            logger.info(f"Sending email to {receiver_email}...")

            # Create email object
            message = MIMEMultipart()
            message['Subject'] = subject
            message['From'] = sender_email
            message['To'] = receiver_email

            # Create HTML body
            html_body = f"""\
            <html>
                <head>
                    <style>
                        table {{
                            width: 80%;
                            border-collapse: collapse;
                            border: 2px solid #ddd;
                            font-family: Arial, sans-serif;
                        }}
                        th, td {{
                            padding: 8px;
                            text-align: left;
                            border-bottom: 1px solid #ddd;
                        }}
                        th {{
                            background-color: #f2f2f2;
                        }}
                    </style>
                </head>
                <body style="text-align: center;">
                    <p style="text-align: center; font-size: 16px;">{body}</p>
            """

            # 添加表格到 HTML 正文中
            for idx, table_df in enumerate(tables, 1):
                html_body += f"<h2>{table_titles[idx - 1]}</h2>" if table_titles else f"<h2>表格 {idx}</h2>"
                html_body += f'<div style="height: 20px;"></div>  <!-- 添加空白行 -->'
                html_body += df_to_html(table_df)

            # 添加图片到 HTML 正文中
            for i, image_path in enumerate(images_paths, 1):
                html_body += f'<div style="height: 20px;"></div>  <!-- 添加空白行 -->'
                html_body += f'<img src="cid:image{i}" style="max-width: 70%; height: auto;">'

            html_body += """
                </body>
            </html>
            """
            message.attach(MIMEText(html_body, 'html'))

            # Add images to the body
            for i, image_path in enumerate(images_paths, 1):
                # Read the image data using base64
                with open(image_path, 'rb') as img_file:
                    img_data = img_file.read()

                # Create the MIME type object for the image and add it to the message
                img_mime = MIMEImage(img_data)
                img_mime.add_header('Content-ID', f'<image{i}>')
                message.attach(img_mime)

            # Send the email
            server.sendmail(sender_email, receiver_email, message.as_string())
            logger.info(f"{c.GREEN}Email successfully sent to {receiver_email}!{c.RESET}")

    except Exception as e:
        logger.error(f"{c.RED}Failed to send email: {e}{c.RESET}")
    finally:
        server.quit()


if __name__ == '__main__':
    # 假设你有一个 DataFrame
    data1 = {'A': [1, 2, 3], 'B': [4, 5, 6]}
    data2 = {'C': [7, 8, 9], 'D': [10, 11, 12]}
    df1 = pd.DataFrame(data1)
    df2 = pd.DataFrame(data2)

    images_paths = [
        os.path.join(os.getcwd(), 'result_push', f"all_market_change_distribution.png"),
        os.path.join(os.getcwd(), 'result_push', 'cumulative_market_value.png')
    ]

    # 调用函数发送邮件，并直接插入图片到正文中
    params = {
        'receiver_email_list': ['handsomevictor0054@gmail.com'],
        'subject': 'Crypto - Solana - Trading Action',
        'body': 'New trades have been executed during the past 5 minutes.',
        'tables': [df1, df2],
        'images_paths': images_paths
    }
    send_email(**params)
