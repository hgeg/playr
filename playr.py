#!/usr/bin/env python
import requests,time,re,os,sys,subprocess,omx
import youtube_dl,thread,logging,libtorrent,HTMLParser
from flask import Flask,request,render_template
from flup.server.fcgi import WSGIServer
app = Flask(__name__)
yturl = r'(?:http(?:s|)://){0,1}(?:www.){0,1}youtu(?:\.be|be\.com)/(?:watch\?v=)([^\?&=]*)'
trurl = r'(http(?:s|)://[^"]*torrent[^"]*)'
queue,qlock,player = [],False,None

def resolve_url(url):
  url = url if 'http' in url else 'http://%s'%url
  vurl = None
  if re.match(trurl,url):
    thread.start_new_thread(download_media,(url,))
    return 'torrent'
  try:
    ydl = youtube_dl.YoutubeDL({'outtmpl': '%(id)s%(ext)s'})
    ydl.add_default_info_extractors()
    result = ydl.extract_info(url,download=False)
    if 'entries' in result: video = result['entries'][0]
    else: video = result
    vurl = video['url']
  except:
    text = requests.get(url).text
    try:
      vurl = re.findall(r'file: "(.*)",',text)[0]
    except:
      vurl = ''
    url = re.findall(r'<iframe [^>]*src=(?:"|\')([^\'"]*(?:mail\.ru|vk)[^\'"]*)(?:"|\')[^>]*',text)[0]
    if 'mail.ru' in url:
      vdict = dict(re.findall(r'"{0,1}(hd|md|sd)"{0,1}:"([^"]*)"',requests.get(url).text))
      vurl = vdict['hd'] if 'hd' in vdict else vdict['md'] if 'md' in vdict else vdict['sd']
    elif 'vk' in url:
      url = HTMLParser.HTMLParser().unescape(url)
      vurl = re.findall(r'(http[^"(http)]*\.720.mp4)',requests.get(url).text)[0]
    elif 'daclip' in url:
      url = HTMLParser.HTMLParser().unescape(url)
      vurl = re.findall(r'(http[^"(http)]*\.mp4)',requests.get(url).text)[0]
  return vurl

def download_media(url):
  cwd = os.getcwd()
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
    s = h.status()
    if ctr==10: ctr = 0
    #TODO: pllay torrents after 10% loading.
    if not playing and s.progress>0.95:
      try:
        playing = True
        subprocess.call(["screen", "-S", "omx", "-X", "quit"])
        subprocess.Popen(['screen','-S','omx','omxplayer','-o','hdmi','media.tmp'])  
      except Exception as e: pass
    time.sleep(2)
    ctr+=1

def play_media(vurl):
  global player
  player = omx.OMXPlayer(vurl)
  while True:
    time.sleep(1)
    if player.finished:
      try:
        player = omx.OMXPlayer(resolve_url(queue.pop(0)))
      except: return      

def control(line):
  global player
  if not player: return
  if "pause" == line: 
    player.pause()
  if "play" == line: 
    player.play()
  if "stop" == line:
    player.stop()
  if "ff" == line:
    player.seek_forward_30()
  if "fff" == line:
    player.seek_forward_250()
  if "rw" == line:
    player.seek_backward_30()
  if "rww" == line:
    player.seek_backward_250()

@app.route("/playr/",methods = ['GET','POST'])
def play():
  global queue,player
  if request.method == 'POST':
    ctrl = request.form['url']
    if ctrl in ('play','pause','stop','ff','rw'):
        control(ctrl)
        state = {'play':'playing','pause':'paused','stop':'http://','ff':'+30 secs','rw':'-30 secs'}
        return "control"+state[ctrl]
    elif 'queue' == ctrl[:5]:
      try:
        queue.append(ctrl.split()[1])
        return "queue:Added to queue"
      except:
        return 'queue:%s'%', '.join([e.split('/')[-1] for e in queue] if queue else ['No items in the queue'])
    elif ctrl == 'clear':
      try:
        queue = []
        return 'Queue cleared' 
      except:
        return 'Cannot access queue'
    try:
      vurl = resolve_url(ctrl)
      if player:
        player.stop()
      thread.start_new_thread(play_media,(vurl,))
      return 'url'
    except Exception as e: return 'Error: %s'%e.message
  else:
    t = render_template('playr.html')
    return t

if __name__ == "__main__":
    #subprocess.Popen(['screen','-S','cecmonitor','cec-client', '-m','RPI', '-f', 'ceclog'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    #thread.start_new_thread(cec,('ceclog',))
    WSGIServer(app).run()
    #app.run(host='0.0.0.0',port=8774,debug=True)
