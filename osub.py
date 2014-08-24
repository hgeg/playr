import os,sys,struct,xmlrpclib,zlib,requests
def OSHash(name): 
  longlongformat = 'q'  # long long 
  bytesize = struct.calcsize(longlongformat) 

  f = open(name, "rb") 

  filesize = os.path.getsize(name) 
  hash = filesize 

  if filesize < 65536 * 2: return "SizeError" 

  for x in range(65536/bytesize): 
    buffer = f.read(bytesize) 
    (l_value,)= struct.unpack(longlongformat, buffer)  
    hash += l_value 
    hash = hash & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number

  f.seek(max(0,filesize-65536),0) 
  for x in range(65536/bytesize): 
    buffer = f.read(bytesize) 
    (l_value,)= struct.unpack(longlongformat, buffer)  
    hash += l_value 
    hash = hash & 0xFFFFFFFFFFFFFFFF 

  f.close() 
  returnedhash =  "%016x" % hash 
  return returnedhash 

def get_subtitle(path):
  try:
      if os.path.isfile(path[:-3]+'srt'): return
      filehash = OSHash(path)
      filesize = int(os.path.getsize(path))
      proxy = xmlrpclib.ServerProxy("http://api.opensubtitles.org/xml-rpc")
      login = proxy.LogIn('hgeg','sokoban','en','torrentor')
      if(login['status']=='200 OK'):
        token = login['token']
        data = proxy.SearchSubtitles(token,[{'moviehash':filehash,'moviebytesize':filesize,'sublanguageid':'eng,en,tr'}])
        content = zlib.decompress(requests.get(data['data'][0]['SubDownloadLink']).content,16+zlib.MAX_WBITS)
        with open(path[:-3]+'srt','wb') as f:
          f.write(content)
        print 'Download successful'
      else: print "Connection Error: %s"%login['status']
  except Exception as e: print "DBError: no subtitle found"

if __name__ == '__main__': get_subtitle(sys.argv[1])
  
