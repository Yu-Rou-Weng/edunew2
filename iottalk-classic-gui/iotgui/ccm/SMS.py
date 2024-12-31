import subprocess

# SMS Setting #
SMS_SERVER_IP = ''
SMS_SERVER_LOGIN = ''
SMS_SERVER_PWD = ''


def send_SMS(msg, tel):
    subprocess.Popen([
        './SMS',
        SMS_SERVER_IP,
        SMS_SERVER_LOGIN,
        SMS_SERVER_PWD,
        tel,
        msg
    ])
