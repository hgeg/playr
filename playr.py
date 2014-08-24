#!/usr/bin/env python
import requests,time,re,os,sys,subprocess,osub
import youtube_dl,thread,logging,libtorrent,HTMLParser
from flask import Flask,request,render_template
from flup.server.fcgi import WSGIServer
app = Flask(__name__)
gurl = r'(?:http(?:s|)://)?(?:www\.)?(.*)\.[^/]*(?:/.*)'
trurl = r'(http(?:s|)://[^"]*torrent[^"]*)'
queue,qlock,resolving,progress = [],False,False,0
CONTROL_DIRECTIVES = ('play','pause','stop','ff','rw','fff','rww','queue','clear','torrent','sf','sb')
YDL_SUPPORTED_SITES = youtube_dl.extractor.__dict__.keys()
VIDEO_TYPES = ('video/mp4','video/webm','video/ogg')

f = open('./templates/playr.html')
index = f.read()
f.close()

def resolve_url(url):
  #downloadr addon
  if os.path.isfile('/media/30c9cdc2-52cd-4ca1-a65c-00d888ec25ff/media/%s'%url):
    osub.get_subtitle('/media/30c9cdc2-52cd-4ca1-a65c-00d888ec25ff/media/%s'%url)
    return '/media/30c9cdc2-52cd-4ca1-a65c-00d888ec25ff/media/%s'%url
  resolving = True
  url = url if 'http' in url else 'http://%s'%url
  vurl = None
  host = re.findall(gurl,url)[0]
  if host in YDL_SUPPORTED_SITES:
    ydl = youtube_dl.YoutubeDL({'outtmpl': '%(id)s%(ext)s'})
    ydl.add_default_info_extractors()
    result = ydl.extract_info(url,download=False)
    if 'entries' in result: video = result['entries'][0]
    else: video = result
    vurl = video['url']
  else:
    #check if direct media
    ctype = requests.head(url).headers['content-type']
    if ctype in VIDEO_TYPES: vurl = url
    else:
      text = requests.get(url).text
      try:
        vurl = re.findall(r'file: "(.*)",',text)[0]
      except:
        vurl = ''
      url = re.findall(r'<iframe [^>]*src=(?:"|\')([^\'"]*(?:mail\.ru|vk|daclip)[^\'"]*)(?:"|\')[^>]*',text)[0]
      if 'mail.ru' in url:
        vdict = dict(re.findall(r'"{0,1}(hd|md|sd)"{0,1}:"([^"]*)"',requests.get(url).text))
        vurl = vdict['hd'] if 'hd' in vdict else vdict['md'] if 'md' in vdict else vdict['sd']
      elif 'vk' in url:
        url = HTMLParser.HTMLParser().unescape(url)
        vurl = re.findall(r'(http[^"(http)]*\.720.mp4)',requests.get(url).text)[0]
      elif 'daclip' in url:
        url = HTMLParser.HTMLParser().unescape(url)
        vurl = re.findall(r'(http[^"(http)]*\.mp4)',requests.get(url).text)[0]
  resolving = False
  return vurl

def play_media():
  global resolving,progress
  while True:
    time.sleep(1)
    if resolving: continue
    try: pcount = int(subprocess.check_output(["pgrep","-f","omxplayer","-c"]))
    except: pcount = 0
    if pcount is 0 and len(queue)>0:
      try:
        progress = 0
        subprocess.Popen(['screen','-dmS','omx','omxplayer','-o','hdmi',queue.pop(0)[1]])
        time.sleep(10)
      except: pass      

def control(line):
  global queue,progress
  if "pause" == line: 
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", 'p'])
    return 'Paused'
  if "play" == line: 
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", 'p'])
    return 'Playing'
  if "stop" == line:
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", 'q'])
    return 'Stopped'
  if "sf" == line:
    [subprocess.call(["screen", "-S", "omx", "-X", "stuff", 'd']) for e in xrange(4)]
    return 'Subtitle Delay: +1 sec'
  if "sb" == line:
    [subprocess.call(["screen", "-S", "omx", "-X", "stuff", 'f']) for e in xrange(4)]
    return 'Subtitle Delay: -1 sec'
  if "fff" == line:
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", '\c[[A'])
    return '+10 mins'
  if "rww" == line:
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", '\c[[B'])
    return '-10 mins'
  if "ff" == line:
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", '\c[[C'])
    return '+30 secs'
  if "rw" == line:
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", '\c[[D'])
    return '-30 secs'
  if "clear" == line:
    queue = []
    return 'Queue cleared'
  if "queue" in line[:6]:
    try:
      p,q = line.split()
      queue.append((q,resolve_url(q)))
      return 'Added to queue'
    except:
      return ', '.join([re.findall(r'http://[^/]+/(.+)?',e[0])[0] for e in queue] if queue else ['No items in the queue'])
  return 'http://'
     

@app.route("/playr/",methods = ['GET','POST'])
def play():
  global queue
  if request.method == 'POST':
    ctrl = request.form['url'].strip()
    if ctrl.split()[0] in CONTROL_DIRECTIVES:
      state = control(ctrl)
      return "control:"+state
    try:
      vurl = resolve_url(ctrl)
      subprocess.call(["screen", "-S", "omx", "-X", "quit"])
      subprocess.Popen(['screen','-dmS','omx','omxplayer','-o','hdmi',vurl])
      return 'url'
    except Exception as e: return 'Error: %s'%e.message
  else:
    #t = render_template('playr.html')
    return index

if __name__ == "__main__":
    thread.start_new_thread(play_media,())
    WSGIServer(app).run()
    #app.run(host='0.0.0.0',port=8774,debug=True)
