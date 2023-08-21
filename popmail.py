import poplib,mailconfig,sys,getpass

mailserver = mailconfig.popservername
mailuser = mailconfig.popusername
mailpasswd = getpass.getpass('Password for %s?' % mailserver)

print('Connecting...')
server = poplib.POP3(mailserver)
server.user(mailuser)
server.pass_(mailpasswd)

try:
    print(server.getwelcome()) #Возвращает приветственную строку
    msgCount,msgBytes = server.stat() #Получение состояния почтового ящика.
    print('There are',msgCount,'main messages in',msgBytes,'bytes')
    print(server.list())
    print('-'*80)
    input('[Press Enter key]')
    
    for i in range(msgCount):
        hdr,message,octets = server.retr(i+1) #получит сообщение с номером i+1 нумерация начинаеться с 1
        for line in message: #octets - счетчик байтов
            print(line.decode())
            print('-'*80)
            if i<msgCount-1:
                input('[Press input key]')
finally:
    server.quit()
print('Bye.')
