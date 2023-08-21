import mailconfig,mailSender,mailFetcher,mailParser
from pymail import inputmessage

mailserver = mailconfig.popservername
mailuser = mailconfig.popusername
mailfile = mailconfig.savemailfile
fetcher = mailFetcher.MailFetcherConsole(mailserver,mailuser)
sender = mailSender.MailSender()
parser = mailParser.MailParser()

mailcache = {}

def fetchmessage(i):
    try:
        fulltext = mailcache[i]
    except KeyError:
        fulltext = fetcher.dowloadMessage(i)
        mailcache[i] = fulltext
    return fulltext

def sendmessage():
    From,To,Subj,text = inputmessage()
    sender.sendMessage(From,To,Subj,[],text,attaches = None)

def deletemessage(toDelete,verify=True):
    print('To be deleted:',toDelete)
    if verify and input('Delete?')[:1] not in ['Y','y']:
        print('Delete cancelled.')
    else:
        print('Deleting messages from server...')
        fetcher.deleteMessages(toDelete)

def showindex(msgList,msgSizes,chunk = 5):
    count = 0
    for (msg,size) in zip(msgList,msgSizes):
        count += 1
        print('%d:\t%d bytes' % (count,size))
        for hdr in ('From','To','Date','Subject'):
            print('\t%-8s=>%s' % (hdr,msg.get(hdr,'(unknown)')))
        if count % chunk == 0:
            input('[Press Enter key]')

def showmessage(i,msgList):
    if 1 <= i <= len(msgList):
        fulltext = fetchmessage(i)
        message = parser.parseMessage(fulltext)
        ctype,mailtext = parser.findMainText(message)
        print('-'*79)
        print(mailtext.rstrip() + '\n')
        print('-'*79)
    else:
        print('Bad message number')

def savemessage(i,mailfile,msgList):
    if 1 <= i <= len(msgList):
        fulltext = fetchmessage(i)
        savefile = open(mailfile,'a',encoding = mailconfig.fetchEncoding)
        savefile.write('\n' + fulltext + '-'*80 + '\n')
    else:
        print('Bad message number')

def msgnum(command):
    try:
        return int(command.split()[1])
    except:
        return -1

helptext  = '''
Available commands:
i - index display
l n? - list all messages (or just message n)
d n? - mark all messages for deletion (or just message n)
s n? - save all messages to a file (or just message n)
m - compose and send a new mail message
q - quit pymail
? - display this help text
'''

def interact(msgList,msgSizes,mailfile):
    showindex(msgList,msgSizes)
    toDelete = []
    while True:
        try:
            command = input('[Pymail] Action? (i,l,d,s,m,q,?) ')
        except EOFError:
            command = 'q'
        
        if not command: command = '*'
        if command == 'q':
            break
        
        elif command[0] == 'i':
            showindex(msgList,msgSizes)
        
        elif command[0] == 'l':
            if len(command) == 1:
                for i in range(1,len(msgList)+1):
                    showmessage(i,msgList)
                else:
                    showmessage(msgnum(command),msgList)
        
        elif command[0] == 's':
            if len(command) == 1:
                for i in range(1,len(msgList)+1):
                    savemessage(1,mailfile,msgList)
            else:
                savemessage(msgnum(command),mailfile,msgList)
        
        elif command[0] == 'd':
            if len(command) == 1:
                toDelete = list(range(1,len(msgList)+1))
            else:
                delnum = msgnum(command)
                if (1 <= delnum <= len(msgList)) and (delnum not in toDelete):
                    toDelete.append(delnum)
                else:
                    print('Bad message number')
        
        elif command[0] == 'm':
            try:
                sendmessage()
            except:
                print('Error - mail not sent')
        
        elif command[0] == '?':
            print(helptext)
        
        else:
            print('What? -- type "?" for commands help')
    return toDelete

def main():
    def progress(i,max):
        print(i,'of',max)
    
    hdrsList,msgSizes,ignore = fetcher.dowloadAllHeaders(progress)
    msgList = [parser.parseHeaders(hdrtext) for hdrtext in hdrsList]
    print('[Pymail email client]')
    toDelete = interact(msgList,msgSizes,mailfile)
    if toDelete: deletemessage(toDelete)
