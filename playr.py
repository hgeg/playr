#!/usr/bin/env python
import requests,time,re,os,sys,subprocess
import youtube_dl,thread,logging,libtorrent,HTMLParser
from flask import Flask,request,render_template
from flup.server.fcgi import WSGIServer
app = Flask(__name__)
yturl = r'(?:http(?:s|)://){0,1}(?:www.){0,1}youtu(?:\.be|be\.com)/(?:watch\?v=)([^\?&=]*)'
trurl = r'(http(?:s|)://[^"]*torrent[^"]*)'
queue,qlock,resolving,progress = [],False,False,0
CONTROL_DIRECTIVES = ('play','pause','stop','ff','rw','queue','clear','torrent')
YDL_SUPPORTED_SITES = youtube_dl.extractor.__dict__.keys()

def resolve_url(url):
  resolving = True
  url = url if 'http' in url else 'http://%s'%url
  vurl = None
  if re.match(trurl,url):
    thread.start_new_thread(download_media,(url,))
    return 'torrent'
  if map(lambda s: s in url, YDL_SUPPORTED_SITES):
    ydl = youtube_dl.YoutubeDL({'outtmpl': '%(id)s%(ext)s'})
    ydl.add_default_info_extractors()
    result = ydl.extract_info(url,download=False)
    if 'entries' in result: video = result['entries'][0]
    else: video = result
    vurl = video['url']
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

def download_media(url):
  cwd = os.getcwd()
  global progress
  progress = 0
  try:
    session = libtorrent.session()
    session.listen_on(6881, 6891)

    tfile = requests.get(url).content
    e = libtorrent.bdecode(tfile)
    info = libtorrent.torrent_info(e)
    info.rename_file(0,'media.tmp')

    h = session.add_torrent(info, cwd, storage_mode=libtorrent.storage_mode_t.storage_mode_compact)
    h.set_sequential_download(True)
    playing = False
    ctr = 10
  except Exception as e: return
  while not h.is_seed(): 
    progress = s.progress*100
    s = h.status()
    if ctr==10: ctr = 0
    if s.progress>0.95:
      queue.append('media.tmp')
    time.sleep(2)
    ctr+=1

def play_media():
  global resolving,progress
  while True:
    time.sleep(1)
    if resolving: 
      time.sleep(5)
      continue
    try:
      pcount = int(check_output(["pgrep","-f","omxplayer","-c"]))
    except: pcount = 0
    if pcount is 0:
      try:
        progress = 0
        subprocess.Popen(['screen','-dmS','omx','omxplayer','-o','hdmi',resolve_url(queue.pop(0))])
      except: pass      

def control(line):
  global queue,progress
  if "pause" == line: 
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", 'p'])
    return 'paused'
  if "play" == line: 
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", 'p'])
    return 'playing'
  if "stop" == line:
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", 'q'])
    return 'http://'
  if "ff" == line:
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", '\c[[C'])
    return '+30 secs'
  if "rw" == line:
    subprocess.call(["screen", "-S", "omx", "-X", "stuff", '\c[[D'])
    return '-30 secs'
  if "clear" == line:
    queue = []
    return 'queue cleared'
  if "torrent" == line:
    return '%d%%'%progress
  if "queue" in line[:5]:
    try:
      p,q = line.split()
      queue.append(q)
      return 'added to queue'
    except:
      return ', '.join([e.split('/')[-1] for e in queue] if queue else ['No items in the queue'])
     

@app.route("/playr/",methods = ['GET','POST'])
def play():
  global queue,player
  if request.method == 'POST':
    ctrl = request.form['url']
    if ctrl in CONTROL_DIRECTIVES:
      state = control(ctrl)
      return "control:"+state
    try:
      vurl = resolve_url(ctrl)
      if player:
        player.stop()
      subprocess.call(["screen", "-S", "omx", "-X", "quit"])
      subprocess.Popen(['screen','-dmS','omx','omxplayer','-o','hdmi',vurl])
      return 'url'
    except Exception as e: return 'Error: %s'%e.message
  else:
    t = render_template('playr.html')
    return t

if __name__ == "__main__":
    thread.start_new_thread(play_media,())
    WSGIServer(app).run()
    #app.run(host='0.0.0.0',port=8774,debug=True)
