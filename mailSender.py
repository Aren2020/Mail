import mailconfig
import smtplib,os,mimetypes
import email.utils,email.encoders,email.header
from mailTool_copy import MailTool,SilentMailTool

from  email.message          import Message
from  email.mime.multipart   import MIMEMultipart
from  email.mime.image       import MIMEImage
from  email.mime.audio       import MIMEAudio
from  email.mime.text        import MIMEText
from  email.mime.base        import MIMEBase
from  email.mime.application import MIMEApplication

def fix_encode_base24(msgobj):
    linelen = 76 #согласно стандартоми MIME
    text = msgobj.get_payload()

    if isinstance(text,bytes):
        text = text.decode('ascii')
    
    lines = []
    while text:
        line,text = text[:linelen],text[linelen:]
        lines.append(line)
    msgobj.set_payload('\n'.join(lines))

def fix_text_required(encodingname):
    from email.charset import Charset,QP,BASE64

    charset = Charset(encodingname)
    bodyenc = charset.body_encode
    return bodyenc in (None,QP) #данные типа str

class MailSender(MailTool):
    def __init__(self,smtpserver = None,tracesize = 256):
        self.smtpServerName = smtpserver or mailconfig.smtpservername
        self.tracesize = tracesize
    
    def sendMessage(self,From,To,Subj,extrahdrs,bodytext,attaches,
                                saveMailSeparator = (('='*80)+'PY\n'),
                                bodytextEncoding = 'us-ascii',
                                attachesEncodings = None ):
        if fix_text_required(bodytextEncoding):
            if not isinstance(bodytext,str):
                bodytext = bodytext.decode(bodytextEncoding)
        else:
            if not isinstance(bodytext,bytes):
                bodytext = bodytext.encode(bodytextEncoding)
        
        #создать корень сообщений
        if not attaches:
            msg = Message()
            msg.set_payload(bodytext,charset = bodytextEncoding)
        else:
            msg = MIMEMultipart()
            self.addAttachments(msg,bodytext,attaches,bodytextEncoding,attachesEncodings)
        
        hdrenc = mailconfig.headersEncodeTo or 'utf-8'
        Subj = self.encodeHeader(Subj,hdrenc)
        From = self.encodeAddrHeader(From,hdrenc)
        To = [self.encodeAddrHeader(T,hdrenc) for T in To]
        Tos = ', '.join(To)

        #добавить заголовки в корень сообщения
        msg['From'] = From
        msg['To'] = Tos
        msg['Subject'] = Subj
        msg['Date'] = email.utils.formatdate()
        recip = To
        for name,value in extrahdrs:
            if value:
                if name.lower() not in ['cc','bcc']:
                    value = self.encodeHeader(value,hdrenc)
                    msg[name]=value
                else:
                    value = [self.encodeAddrHeader(V,hdrenc) for V in value]
                    recip+= value
                    if name.lower() != 'bcc':
                        msg[name]=', '.join(value)
        recip = list(set(recip))
        fulltext = msg.as_string()
        self.trace('Sending to...',str(recip))
        self.trace(fulltext[:self.tracesize])

        server = smtplib.SMTP(self.smtpServerName,timeout = 15)
        self.getPassword()
        self.authenticateServer(server)
        try:
            failed = server.sendmail(From,recip,fulltext)
        except:
            server.close()
            raise
        else:
            server.quit()
        self.saveSendMessage(fulltext,saveMailSeparator)

        if failed:
            class SomeAddrsFailed(Exception): pass
            raise SomeAddrsFailed('Failed addrs:%s\n' % failed) 
        self.trace('Send exit') 

    def addAttachments(self,mainmsg,bodytext,attaches,bodytextencode,attachesEncodings):
        #добавить главную часть
        msg = MIMEText(bodytext,_charset = bodytextencode)
        mainmsg.attach(msg)
     
        #добавить части с вложениями
        encodings = attachesEncodings or (['us-ascii'] * len(attaches))
        for (filename,fileencode) in zip(attaches,encodings):
            if not os.path.isfile(filename):
                continue
        
            contype,encoding = mimetypes.guess_type(filename)
            if contype is None or encoding is not None:
                contype = 'application/octet-stream' #универсальный тип
            self.trace('Adding '+contype)
            
            maintype,subtype = contype.split('/',1)
            if maintype == 'text':
                if fix_text_required(fileencode):
                    data = open(filename,'r',encoding=fileencode)
                else:
                    data = open(filename,'rb')
                msg = MIMEText(data.read(),_subtype = subtype,_charset = fileencode)
                data.close()
            
            elif maintype == 'image':
                data = open(filename,'rb')
                msg = MIMEImage(data.read(),_subject = subtype,_encoder = fix_encode_base24)
                data.close()
            
            elif maintype == 'audio':
                data = open(filename,'rb')
                msg = MIMEAudio(data.read(),_subtype = subtype,_encoder = fix_encode_base24)
                data.close()
            
            elif maintype == 'application':
                data = open(filename,'rb')
                msg = MIMEApplication(data.read(),_subtype = subtype,_encoder = fix_encode_base24)
                data.close()
            else:
                data = open(filename,'rb')
                msg = MIMEBase(maintype,subtype)
                msg.set_payload(data.read())
                data.close()
                fix_encode_base24(msg)
            
            basename = os.path.basename(filename)
            msg.add_header('Content-Disposition','attachment',filename = basename)
            mainmsg.attach(msg)
        mainmsg.preamble = 'A multi-part MIME format message.\n'
        mainmsg.epilogue = ''
    def saveSendMessage(self,fulltext,saveMailSeparator):
        try:
            sentfile = open(mailconfig.sentmainfile,'a',encoding= mailconfig.fetchEncoding)
            if fulltext[-1] != '\n':fulltext +='\n'
            sentfile.write(saveMailSeparator)
            sentfile.write(fulltext)
            sentfile.close()
        except:
            self.trace('Could not save sent message')
    
    def encodeHeader(self,headertext,unicodeencoding = 'utf-8'):
        try:
            headertext.encode('ascii')
        except:
            try:
                hdrobj = email.header.make_header([(headertext,unicodeencoding)])
                headertext = hdrobj.encode()
            except:
                pass
    
    def encodeAddrHeader(self,headertext,unicodeencoding = 'utf-8'):
        try:
            pairs = email.utils.getaddresses([headertext])#разбить на части

            encoded = []
            for name,addr in pairs:
                try:
                    name.encode('ascii')
                except  UnicodeError:
                    try:
                        uni = name.encode(unicodeencoding)
                        hdr = email.header.make_header([(uni,unicodeencoding)])
                        name = hdr.encode()
                    except:
                        name = None
                joined = email.utils.formataddr((name,addr))
                encoded.append(joined)
            fullhdr = ', '.join(encoded)
            if len(fullhdr) >72 or '\n' in fullhdr:
                fullhdr = ',\n'.join(encoded)
            return fullhdr
        except:
            return self.encodeHeader(headertext)
    def authenticateServer(self,server):
        pass
    def getPassword(self):
        pass

class MailSenderAuth(MailSender):
    smtpPassword = None
    def __init__(self,smtpserver = None,smtpuser = None):
        MailSender.__init__(self,smtpserver)
        self.smtpUser =smtpuser
    def authenticateServer(self,server):
        server.login(self.smtpUser,self.smtpPassword)

    def getPassword(self):
        if not self.smtpPassword:
            try:
                localfile = open(mailconfig.smtppasswdfile)
                MailSenderAuth.smtpPassword = localfile.readline()[:-1]
                self.trace('local file password' + repr(self.smtpPassword))
            except:
                MailSenderAuth.smtpPassword = self.askSmtpPassword()
    def askSmtpPassword(self):
        assert False, 'Subclass must define method'

class MailSenderAuthConsole(MailSenderAuth):
    def askSmtpPassword(self):
        import getpass
        return getpass.getpass()

class SilentMailSender(SilentMailTool,MailSender):
    pass 
