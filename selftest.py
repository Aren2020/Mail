import mailFetcher,mailParser,mailSender,mailconfig
print('config:',mailconfig.__file__)

if not mailconfig.smtpuser:
    sender = mailSender.MailSender(tracesize=5000)
else:
    sender = mailSender.MailSenderAuthConsole(tracesize = 5000)

sender.sendMessage(From      = mailconfig.myaddress,
                   To        = [mailconfig.myaddress],
                   Subj      = 'testing.mailtools.packet',
                   extrahdrs = [('X-Mailer','mailtools')],
                   bodytext  = 'Here is my source code\n',
                   attaches  = ['selftest.py']
) 
fetcher = mailFetcher.MailFetcherConsole()
def status(*args): print(args)

hdrs,sizes,loadedall = fetcher.dowloadAllHeaders(status)
for num,hdr in enumerate(hdrs[:5]):
    print(hdr)
    if input('load mail?') in ['y','Y']:
        print(fetcher.dowloadMessage(num+1).rstrip(),'\n','-'*70)

last5 = len(hdrs)-4
msgs,sizes,loadedall = fetcher.dowloadedAllMessages(status,loadfrom = last5)
for msg in msgs:
    print(msg[:200],'\n','-'*70)

parser = mailParser.MailParser()
for i in [0]:
    fulltext = msgs[i]
    message = parser.parseMessage(fulltext)
    ctype,maintext = parser.findMainText(message)
    print('Parsed:',message['Subject'])
    print(maintext)
input('Press Enter to exit')
