import poplib,mailconfig,sys
print('user:',mailconfig.popusername)

from mailTool_copy import MailTool,SilentMailTool
from mailParser_copy import MailParser

class DeleteSynchError(Exception):  pass # обнорудена рассинхронизация при удалении
class TopNotSupported(Exception):   pass # невозможно выполнить синхронизацию
class MassageSynchError(Exception): pass # обноружена рассинхронизация оглавления

class MailFetcher(MailTool):
    def __init__(self,popserver = None,popuser = None,poppswd = None,hastop = True):
        self.popServer = popserver
        self.popUser = popuser
        self.popPassword = poppswd
        self.srvrHasTop = hastop
    
    def connect(self):
        self.trace('conneting...')
        self.getPassword()
        server = poplib.POP3(self.popServer,timeout = 15)
        server.user(self.popUser)
        server.pass_(self.popPassword)
        self.trace(server.getwelcome())
        return server
    
    fetchEncoding = mailconfig.fetchEncoding
    def decodeFullText(self,messageBytes):
        text = None
        kinds = [self.fetchEncoding]
        kinds += ['ascii','latin1','utf8']
        kinds += [sys.getdefaultencoding()]
        for kind in kinds:
            try:
                text = [line.decode(kind) for line in messageBytes]
                break
            except (UnicodeError,LookupError):
                pass
        
        if text == None:
            blankline = messageBytes.index(b'')
            hdrsonly = messageBytes[:blankline]
            commons = ['ascii','latin1','utf8']
            for common in commons:
                try:
                    text = [line.decode(common) for line in hdrsonly]
                    break
                except UnicodeError:
                    pass
            else:
                try:
                    text = [line.decode() for line in hdrsonly]
                except UnicodeError:
                    text = ['From: (sender of unknown Unicode format headers)']
            text+=['',
            '--Sorry: mailtools cannot decode this mail content!--']
        return text

    def dowloadMessage(self,msgnum):
        self.trace('load '+str(msgnum))
        server = self.connect()
        try:
            resp,msglines,respsz = server.retr(msgnum)
        finally:
            server.quit()
        msglines = self.decodeFullText(msglines)
        return '\n'.join(msglines)
    
    def dowloadAllHeaders(self,progress = None,loadfrom = 1):
        if not self.srvrHasTop:
            #загрузить полные сообщение
            return self.dowloadedAllMessages(progress,loadfrom)
        else:
            self.trace('loading headers...')
            fetchlimit = mailconfig.fetchlimit
            server = self.connect()
            
            try:
                resp,msginfos,respsz = server.list()
                msgCount = len(msginfos)
                msginfos = msginfos[loadfrom-1:]
                allsizes = [int(x.split()[1]) for x in msginfos]
                allhdrs =  []
                for msgnum in range(loadfrom,msgCount+1):
                    if progress: progress(msgnum,msgCount)
                    if fetchlimit and (msgnum <= msgCount - fetchlimit):
                        hdrtext = 'Subject: --mail skipped-- \n\n'
                        allhdrs.append(hdrtext)
                    else:
                        resp,hdrlines,respsz = server.top(msgnum,0)
                        hdrlines = self.decodeFullText(hdrlines)
                        allhdrs.append('\n'.join(hdrlines))
            finally:
                server.quit()
            assert len(allhdrs) == len(allsizes)            
            self.trace('load headers exit')
            return allhdrs,allsizes,False
    def dowloadedAllMessages(self,progress = None,loadfrom = 1):
        self.trace('loading full messages')
        fetchlimit = mailconfig.fetchlimit
        server = self.connect()
        try:
            (msgCount,msgBytes) = server.stat()
            allmsgs = []
            allsize = []
            for i in range(loadfrom,msgCount):
                if progress: progress(i,msgCount)
                if fetchlimit and (i <= msgCount - fetchlimit):
                    mailtext = 'Subject: --mail skipped--\n\nMail skipped.\n'
                    allmsgs.append(mailtext)
                    allsize.append(len(mailtext))
                else:
                    (resp,message,respsz) = server.retr(i)
                    message = self.decodeFullText(message)
                    allmsgs.append('\n'.join(message))
                    allsize.append(respsz)
        finally:
            server.quit()
        assert len(allmsgs) ==  (msgCount - loadfrom) + 1 #проверка:нумерация с 1
        return allmsgs,allsize,True
    
    def deleteMessages(self,msgnums,progress = None):
        self.trace('deleting mails')
        server = self.connect()
        try:
            for (ix,msgnum) in enumerate(msgnums):
                if progress:progress(ix+1,len(msgnums))
                server.dele(msgnum)
        finally:
            server.quit()
    
    def deleteMessagesSafely(self,msgnums,synchHeaders,progress = None):
        if not self.srvrHasTop:
            raise TopNotSupported('Safe delete cancelled')
        
        self.trace('deleting mails safely')
        errmsg = 'cannot delete %s mail'
        server = self.connect()

        try:
            (msgCount,msgBytes) = server.stat()
            for (ix,msgnum) in enumerate(msgnums):
                if progress: progress(ix+1,len(msgnums))
                if msgnum > msgCount:
                    raise DeleteSynchError(errmsg % msgnum)
                resp,hdrlines,respsz = server.top(msgnum,0)
                hdrlines = self.decodeFullText(hdrlines)
                msghdrs = '\n'.join(hdrlines)
                if not self.headersMatch(msghdrs,synchHeaders[msgnum-1]):
                    raise DeleteSynchError(errmsg % msgnum)
                else:
                    server.dele(msgnum)
        finally:
            server.quit()
    
    def headersMatch(self,hdrtext1,hdrtext2):
        if hdrtext1==hdrtext2:
            self.trace('Same headers text')
            return True
        
        split1 = hdrtext1.splitlines() #str.split('\n') без поледнего ''
        split2 = hdrtext2.splitlines()
        strip1 = [line for line in split1 if not line.startswith('Status:')]
        strip2 = [line for line in split2 if not line.startswith('Status:')]
        if strip1==strip2:
            self.trace('Same without Status')
            return True
        
        #попробовать найти загаловок message-id
        msgid1 = [line for line in split1 if line[:11].lower() == 'message-id']
        msgid2 = [line for line in split2 if line[:11].lower() == 'message-id']
        if (msgid1 or msgid2)  and (msgid1!=msgid2):
            self.trace('Different message-id')
            return False
        
        #полный анализ
        tryheaders = ('From','To','Subject','Date')
        tryheaders += ('Cc','Return-Path','Received')
        msg1 = MailParser().parseHeaders(hdrtext1)
        msg2 = MailParser().parseHeaders(hdrtext2)
        for hdr in tryheaders:
            if msg1.get_all(hdr) != msg2.get_all(hdr):
                self.trace('Diff common headers')
                return False
        else:
            self.trace('Same common headers')
            return True
    
    def getPassword(self):
        if not self.popPassword:
            try:
                localfile = open(mailconfig.poppasswdfile)
                self.popPassword = localfile.readlines()[:-1]
                self.trace('local file password' + repr(self.popPassword))
            except:
                self.popPassword = self.askPopPassword()
    
    def askPopPassword(self):
        assert False,'Subclass must define method'

class MailFetcherConsole(MailFetcher):
    def askPopPassword(self):
        import getpass
        return getpass.getpass()

class SilentMailFetcher(SilentMailTool,MailFetcher):
    pass

