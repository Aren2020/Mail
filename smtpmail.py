import smtplib,sys,email.utils,mailconfig
mailserver = mailconfig.smtpservername

From = input('From?').strip() # адрес отправителя
To = input('To?').strip()     # кому отправить 
Tos = To.split(';')           # может быть больше одного получателя
Subj = input('Subj?').strip()
Date = email.utils.formatdate() #текущие дата и время

text = ('From %s\nTo: %s\nDate: %s\nSubject: %s\n\n' % (From,To,Date,Subj))
print('Type message text,end with line=[Ctrl+d (Unix),Ctrl+z (windows)]')
while True:
    line = sys.stdin.readline()
    if not line:
        break
    text+=line
print('Connecting...')
server = smtplib.SMTP(mailserver)
failed = server.sendmail(From,Tos,text)
server.quit()
if failed:
    print('Failed recipients:',failed)
else:
    print('No errors.')
print('Bye.')
