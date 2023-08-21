import os,mimetypes,sys
import email.parser
import email.header
import email.utils
from email.message import Message
from mailTool_copy import MailTool

class MailParser(MailTool):
    def walkNamedParts(self,message):
        for (ix,part) in enumerate(message.walk()):
            fulltype = part.get_content_type()
            maintype = part.get_content_maintype()
            if maintype == 'multipart':
                continue
            elif fulltype == 'message/rfc822':
                continue
            else:
                filename,contype = self.partName(part,ix)
                yield (filename,contype,part)
    
    def partName(self,part,ix):
        filename =  part.get_filename() #имя файла в загаловке?
        contype = part.get_content_type()
        if not filename:
            filename = part.get_param('name') #проверить параметр name
        if not filename:
            if contype == 'text\plain':
                ext = '.txt'
            else:
                ext = mimetypes.guess_extension(part)
                if not ext: ext = '.bin' #универсальный тип
            filename = 'part-%03d%s' % (ix,ext)
        return (filename,contype)
    
    def saveParts(self,savedir,message):
        if not os.path.exists(savedir):
            os.mkdir(savedir)
        partfiles = []
        for (filename,contype,part) in self.walkNamedParts(message):
            fullname = os.path.join(savedir,filename)
            fileobj = open(fullname,'wb')
            content = part.get_payload(decode = 1)
            if not isinstance(content,bytes):
                content = b'(No Content)'
            fileobj.write(content)
            fileobj.close()
            partfiles.append((contype,fullname))
        return partfiles
    
    def saveOnePart(self,savedir,partname,message):
        if not os.path.exists(savedir):
            os.mkdir(savedir)
        fullname = os.path.join(savedir,partname)
        (contype,content) = self.findOnePart(partname,message)
        if not isinstance(content,bytes):
            content = b'(No Content)'
        open(fullname,'wb').write(content)
        return (contype,fullname)
    
    def partsList(self,message):
        vaildParts = self.walkNamedParts(message)
        return [filename for (filename,contype,part) in vaildParts]
    
    def findOnePart(self,partname,message):
        for (filename,contype,part) in self.walkNamedParts(message):
            if filename==partname:
                content = part.get_payload(decode=1)
                return (contype,content)
    
    def decodedPayload(self,part,asStr = True):
        payload = part.get_payload(decode=1)
        if asStr and isinstance(payload,bytes):
            tries = []
            enchdr = part.get_content_charset() # сначала проверяет наличие кадировки в загаловке
            if enchdr:
                tries+=[enchdr]
            tries+=[sys.getdefaultencoding()] # то же что и payload.decode()
            tries+=['latin1','utf8'] # наиболее распростронные кадировки
            for trie in tries:
                try:
                    payload = payload.decode(trie)
                    break
                except (UnicodeError,LookupError):
                    pass
            else:
                payload = '--Sorry:cannot decode Unicode text--'
        return payload

    def findMainText(self,message,asStr = True):
        #отыскать простой текст
        for part in message.walk():
            type = part.get_content_type()
            if type == 'text/plain':
                return type,self.decodedPayload(part,asStr)
        
        #текстовой тип с разметкой html
        for part in message.walk():
            type = part.get_content_type()
            if type == 'text/html':
                return type,self.decodedPayload(part,asStr)

        #любой кто с текстовым типом
        for part in message.walk():
            maintype = part.get_content_maintype()
            if maintype == 'text':
                return part.get_content_type(),self.decodedPayload(part,asStr)
        
        #не найдено ничего
        failtext = '[No text to display]' if asStr else b'[No text to display]'
        return 'text/plain',failtext
    
    def decodeHeader(self,rawheader):
        try:
            parts = email.header.decode_header(rawheader)
            decoded = []
            for (part,enc) in parts:
                if enc == 'None':
                    if not isinstance(part,bytes):
                        decoded+=[part]
                    else:
                        decoded+=[part.decode('raw-unicode-escape')]
                else:
                    decoded += [part.decode(enc)]
            return ' '.join(decoded)
        except:
            return rawheader #вернуть как есть

    def decodeAddrHeader(self,rawheader):
        try:
            pairs = email.utils.getaddresses([rawheader])
            decoded = []
            for (name,addr) in pairs:
                try:
                    name = self.decodeHeader(name) 
                except:
                    name = None
                joined = email.utils.formataddr(name,addr)
                decoded.append(joined)
            return ', '.join(decoded)
        except:
            return self.decodeHeader(rawheader)

    def splitAddresses(self,field):
        try:
            pairs = email.utils.getaddresses([field]) #[(name,addr)]
            return [email.utils.formataddr(pair) for pair in pairs] #[name <addr>] 
        except:
            return ''
    
    errorMessage = Message()
    errorMessage.set_payload('[Unable to parse message - format error]')

    def parseHeaders(self,fulltext):
        try:
            return email.parser.Parser().parsestr(fulltext,headersonly=True)
        except:
            return self.errorMessage
    
    def parseMessage(self,fulltext):
        try:
            return email.parser.Parser().parsestr(fulltext)
        except:
            return self.errorMessage
    
    def parseMessageRaw(self,fulltext):
        try:
            return email.parser.HeaderParser().parsestr(fulltext) #только заголовки
        except:
            return self.errorMessage    