# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from xbmcswift2 import Plugin, ListItem
from collections import namedtuple
from datetime import date, datetime, timedelta, tzinfo
from language import get_string
from language import get_string as _
from re import search
import base64
import calendar
import chardet
import ctypes
import glob
import gzip
import io
import json
import math
import os, os.path
import platform
import random
import re
import requests
import shutil
import sqlite3
import stat
import subprocess
import threading
import time
import unicodedata
import uuid

try:
    from urllib.parse import quote, quote_plus, unquote_plus
    from html import unescape as html_unescape
    from io import StringIO
    class HTMLParser:
        def unescape(self, string):
            return html_unescape(string)
except ImportError:
    from urllib import quote, quote_plus, unquote_plus
    from HTMLParser import HTMLParser
    from StringIO import StringIO

import uuid
from kodi_six import xbmc, xbmcaddon, xbmcvfs, xbmcgui
from kodi_six.utils import encode_decode


def addon_id():
    return xbmcaddon.Addon().getAddonInfo('id')


def log(v):
    xbmc.log(repr(v), xbmc.LOGINFO)


addon = xbmcaddon.Addon()
plugin = Plugin()
big_list_view = True
utc_offset = 0
output_format = ''

@encode_decode
def plugin_url_for(plugin, *args, **kwargs):
    return plugin.url_for(*args, **kwargs)

if plugin.get_setting('multiline', str) == "true":
    CR = "[CR]"
else:
    CR = ""

def get_icon_path(icon_name):
    return "special://home/addons/%s/resources/img/%s.png" % (addon_id(), icon_name)

def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]", '', label, flags=re.I)
    label = re.sub(r"\[/?COLOR.*?\]", '', label, flags=re.I)
    return label

def escape( str ):
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str

def unescape( str ):
    str = str.replace("&lt;", "<")
    str = str.replace("&gt;", ">")
    str = str.replace("&quot;", "\"")
    str = str.replace("&amp;", "&")
    return str

def check_has_db_filled_show_error_message_ifn(db_cursor):
    table_found = db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='streams'").fetchone()
    if not table_found:
        xbmcgui.Dialog().notification("IPTV Archive Downloader",
                                      addon.getLocalizedString(30052))
        return False
    return True

@plugin.route('/play_channel/<channelname>')
def play_channel(channelname):
    conn = sqlite3.connect(xbmcvfs.translatePath('%sxmltv.db' % plugin.addon.getAddonInfo('profile')))
    c = conn.cursor()
    if not check_has_db_filled_show_error_message_ifn(c):
        return

    channel = c.execute("SELECT url FROM streams WHERE name=?", (channelname, )).fetchone()

    if not channel:
        return
    url = channel[0]
    #plugin.set_resolved_url(url)
    xbmc.Player().play(url)

@plugin.route('/play_external/<path>')
def play_external(path):
    cmd = [plugin.get_setting('external.player', str)]

    args = plugin.get_setting('external.player.args', str)
    if args:
        cmd.append(args)

    cmd.append(xbmcvfs.translatePath(path))

    subprocess.Popen(cmd,shell=windows())


def xml2local(xml):
    #TODO combine
    return utc2local(xml2utc(xml))


def utc2local(utc):
    timestamp = calendar.timegm(utc.timetuple())
    local = datetime.fromtimestamp(timestamp)
    return local.replace(microsecond=utc.microsecond)


def str2dt(string_date):
    format ='%Y-%m-%d %H:%M:%S'
    try:
        res = datetime.strptime(string_date, format)
    except TypeError:
        res = datetime(*(time.strptime(string_date, format)[0:6]))
    return utc2local(res)


def total_seconds(td):
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6


def windows():
    if os.name == 'nt':
        return True
    else:
        return False


def android_get_current_appid():
    with open("/proc/%d/cmdline" % os.getpid()) as fp:
        return fp.read().rstrip("\0")


def ffmpeg_location():
    ffmpeg_src = xbmcvfs.translatePath(plugin.get_setting('ffmpeg', str))

    if xbmc.getCondVisibility('system.platform.android'):
        ffmpeg_dst = '/data/data/%s/ffmpeg' % android_get_current_appid()

        if (plugin.get_setting('ffmpeg', str) != plugin.get_setting('ffmpeg.last', str)) or (not xbmcvfs.exists(ffmpeg_dst) and ffmpeg_src != ffmpeg_dst):
            xbmcvfs.copy(ffmpeg_src, ffmpeg_dst)
            plugin.set_setting('ffmpeg.last',plugin.get_setting('ffmpeg', str))

        ffmpeg = ffmpeg_dst
    else:
        ffmpeg = ffmpeg_src

    if ffmpeg:
        try:
            st = os.stat(ffmpeg)
            if not (st.st_mode & stat.S_IXUSR):
                try:
                    os.chmod(ffmpeg, st.st_mode | stat.S_IXUSR)
                except:
                    pass
        except:
            pass
    if xbmcvfs.exists(ffmpeg):
        return ffmpeg
    else:
        xbmcgui.Dialog().notification("IPTV Archive Downloader",
                                      addon.getLocalizedString(30056))


def debug_dialog(line2, line3, line4):
    xbmcgui.Dialog().ok("Debugging", line2, line3, line4)


def add_to_queue(channelname, name, start, stop):
    filename = str(stop + '-' + channelname + ' - ' + name + ' - ' + start + ' - ' + stop)
    filename = sane_filename(filename)
    filename = filename[:50]
    # log(filename)
    addon_data = xbmcvfs.translatePath(plugin.addon.getAddonInfo('profile'))
    dir = os.path.join(addon_data, 'queue')
    xbmcvfs.mkdirs(dir)
    path = os.path.join(dir, filename)
    queue_file_path = path + '.queue'
    queue_file = open(queue_file_path, 'w', encoding='utf-8')
    queue_nfo = [f'{channelname}\n', f'{name}\n',f'{start}\n',f'{stop}\n']
    queue_file.writelines((queue_nfo))
    queue_file.close()
    xbmcgui.Dialog().notification("{}: {}".format(
        addon.getLocalizedString(30079), channelname), name, sound=True)
    manage_queue()

def sane_filename(filename):
    filename = filename.replace(':','_')
    filename = filename.replace('/','_')
    filename = filename.replace('?','_')
    filename = filename.replace('!','_')
    filename = filename.replace('\\','_')
    filename = filename.replace(' ','_')
    return filename

def log_queue():
    log("-------------------- Queue -------------------")
    addon_data = xbmcvfs.translatePath(plugin.addon.getAddonInfo('profile'))
    dir = os.path.join(addon_data, 'queue')
    list_of_queue_files = sorted(glob.glob(dir + "/*.*"))
    for count, queue_file_path in enumerate(list_of_queue_files):
        queue_file_data = queue_item_details(queue_file_path)
        log("{}. Channel: {} / Title: {} / Start: {} / Stop: {}".format(count + 1, queue_file_data[0], queue_file_data[1], queue_file_data[2], queue_file_data[3]))
    log("---------------- End of queue ----------------")
    return list_of_queue_files

def queue_item_details(queue_file_path):
    queue_file = open(queue_file_path, 'r', encoding='utf-8')
    queue_data = queue_file.read().splitlines()
    channelname = queue_data[0]
    name = queue_data[1]
    start = utc2local(get_utc_from_string(queue_data[2]))
    stop = utc2local(get_utc_from_string(queue_data[3]))
    queue_file.close()
    return [channelname, name, start, stop]

def check_queued_items():
    list_of_queue_files = log_queue()
    for queue_file in list_of_queue_files: 
        log(queue_file)
        if search('progress', queue_file):
            if not (xbmcgui.Dialog().yesno("IPTV Archive Downloader", addon.getLocalizedString(30080))):
                return
            else:
                os.rename(queue_file, os.path.splitext(queue_file)[0] + ".queue")
                manage_queue()
        

def manage_queue():
    queue_thread = threading.Timer(300,manage_queue)
    list_of_queue_files = log_queue()
    for queue_file in list_of_queue_files: 
        log(queue_file)
        if search('progress', queue_file):
            log("Currently recording: {}".format(plugin.get_setting('current.queue')))
            queue_thread.cancel()
            return
    queue_thread.start()
            
    if list_of_queue_files:
        queue_file_data = queue_item_details(list_of_queue_files[0])
        log("First queue item: {}".format(queue_file_data))
        channelname = queue_file_data[0]
        name = queue_file_data[1]
        start = queue_file_data[2]
        stop = queue_file_data[3]
        after = int(plugin.get_setting('minutes.after', str) or "0")
        local_endtime = stop + timedelta(minutes=after)
        if local_endtime > datetime.now():
            log("Waiting...")
            return
        do_refresh = False
        watch = False
        remind = False
        channelid = None
        queue_file_path = list_of_queue_files[0]
        plugin.set_setting('current.queue', os.path.basename(queue_file_path))
        queue_thread.cancel()
        recording = threading.Thread(target=record_once_thread,args=[None, do_refresh, watch, remind, channelid, channelname, start, stop, False, name, queue_file_path])
        recording.start()

@plugin.route('/record_epg/<channelname>/<name>/<start>/<stop>')
def record_epg(channelname, name, start, stop):
    add_to_queue(channelname, name, start, stop)
# Redundant

# @plugin.route('/record_from_list/<channelname>/<start>/<stop>')
# def record_from_list(channelname, start, stop):
#     start = get_utc_from_string(start)
#     stop = get_utc_from_string(stop)
#     watch = False
#     remind = False
#     channelid = None
#     threading.Thread(target=record_once_thread, args=[None, do_refresh, watch, remind, channelid, channelname, start, stop, False, name]).start()


def get_utc_from_string(date_string):
    utcnow = datetime.utcnow()    
    ts = time.time()
    global utc_offset
    utc_offset = total_seconds(datetime.fromtimestamp(ts) - datetime.utcfromtimestamp(ts))
    r = re.search(r'(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):\d{2}', date_string)
    if r:
        year, month, day, hour, minute = r.group(1), r.group(2), r.group(3), r.group(4), r.group(5)
        return utcnow.replace(day=int(day), month=int(month), year=int(year), hour=int(hour), minute=int(minute),
                              second=0, microsecond=0) - timedelta(seconds=utc_offset)

def write_in_file(file, string):
    file.write(bytearray(string.encode('utf8')))

def record_once_thread(programmeid, do_refresh=True, watch=False, remind=False, channelid=None, channelname=None, start=None,stop=None, play=False, title=None, queue_file_path=None):
    log("Recording: {} - {}, {} - {}".format(channelname, title, start, stop))
    new_queue_file_path = os.path.splitext(queue_file_path)[0] + ".progress"
    os.rename(queue_file_path, new_queue_file_path)
    plugin.set_setting('current.queue', os.path.basename(new_queue_file_path))
    conn = sqlite3.connect(xbmcvfs.translatePath('%sxmltv.db' % plugin.addon.getAddonInfo('profile')), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    cursor = conn.cursor()
    if not check_has_db_filled_show_error_message_ifn(cursor):
        return
   
    programme = {}
  
    if channelid is not None:
        programme["channelid"] = channelid
    if start:
        programme["start"] = datetime2timestamp(start)
    if stop:
        programme["stop"] = datetime2timestamp(stop)

    nfo = {}
    nfo["programme"] = programme

    if not start and not stop:
        return
    
    local_starttime = start
    local_endtime = stop
    channel = ''

    # if channelid:
    #     channel = cursor.execute("SELECT name, url FROM streams WHERE tvg_id=? AND tvg_name=?", (channelid, channelname)).fetchone()
    #     if not channel:
    #         channel = cursor.execute("SELECT name, url FROM streams WHERE tvg_id=? AND name=?", (channelid, channelname)).fetchone()
    # else:
    #     channel = cursor.execute("SELECT name, url FROM streams WHERE name=?", (channelname)).fetchone()
    #     if not channel:
    #         channel = cursor.execute("SELECT name, url FROM streams WHERE tvg_name=?", (channelname)).fetchone()
    
    channel = cursor.execute("SELECT name, url FROM streams WHERE name=? OR tvg_id=? OR tvg_name=?", (channelname, channelname, channelname)).fetchone()

    if not channel:
        log("--------------------------> No channel {} {}".format(channelname, xbmc.LOGERROR))
        return
    else:
        log("--------------------------> Channel: {}".format(channelname))
        # return
    name, url = channel
    if not channelname:
        channelname = name
    nfo["channel"] = {"channelname":channelname}
    if not url:
        log("No url for {} {}".format(channelname, xbmc.LOGERROR))
        return

    url_headers = url.split('|', 1)
    url = url_headers[0]

    headers = {}
    if len(url_headers) == 2:
        sheaders = url_headers[1]
        aheaders = sheaders.split('&')
        if aheaders:
            for h in aheaders:
                k, v = h.split('=', 1)
                headers[k] = unquote_plus(v)

    ftitle = sane_name(title)
    fchannelname = sane_name(channelname)
    fepisode = ""
    try:
        fepisode = re.search(r'(S\d+E\d+)|(S\d+|E\d+)', xbmc.getInfoLabel("ListItem.Plot")).group(0)
    except:
        log("Not a series")
    folder = ""
    if (plugin.get_setting('subfolder', str) == 'true'):
        folder = fchannelname
    if ftitle:
        if fepisode:
            filename = "%s - %s - %s - %s" % (ftitle, fepisode, fchannelname, local_starttime.strftime("%Y-%m-%d %H-%M"))
        else:
            filename = "%s - %s - %s" % (ftitle, fchannelname, local_starttime.strftime("%Y-%m-%d %H-%M"))
    else:
        filename = "%s - %s" % (fchannelname, local_starttime.strftime("%Y-%m-%d %H-%M"))

    
    before = int(plugin.get_setting('minutes.before', str) or "0")
    after = int(plugin.get_setting('minutes.after', str) or "0")
    local_starttime = local_starttime - timedelta(minutes=before)
    local_endtime = local_endtime + timedelta(minutes=after)
  
    now = datetime.now()   
    if (local_starttime < now) and (local_endtime > now):
        local_starttime = now
        # immediate = True
        past_recording = False
        xbmcgui.Dialog().ok(addon.getLocalizedString(30050),
                            addon.getLocalizedString(30051))
        return
    elif (local_starttime < now) and (local_endtime < now):
        # immediate = True
        # local_starttime = now
        past_recording = True
    else:
        # immediate = False
        past_recording = False
        xbmcgui.Dialog().ok(addon.getLocalizedString(30050),
                            addon.getLocalizedString(30051))
        return

    kodi_recordings = xbmcvfs.translatePath(plugin.get_setting('recordings', str))
    ffmpeg_recordings = plugin.get_setting('ffmpeg.recordings', str) or kodi_recordings

    dir = os.path.join(kodi_recordings, folder)
    ffmpeg_dir = os.path.join(ffmpeg_recordings, folder)
    xbmcvfs.mkdirs(dir)
    path = os.path.join(dir, filename)
    json_path = path + '.json'
    nfo_path = path + '.nfo'
    jpg_path = path + '.jpg'
    # if (plugin.get_setting('output.format') == "0"): # mkv
    #     output_format="mkv"
    # if (plugin.get_setting('output.format') == "1"): # ts
    #     output_format="ts"
    path = path + '.ts'
    log(path)
    path = path.replace("\\", "\\\\")
    ffmpeg = ffmpeg_location()
    if not ffmpeg:
        return
   
    # Get artwork
    if plugin.get_setting('artwork', bool):
        artwork_url_temp = xbmc.getInfoLabel("ListItem.Icon")
        artwork_url = str(re.search('@(.*)/', artwork_url_temp).group(1)).replace('%3a',':').replace('%2f','/')

        r = requests.get(artwork_url, stream=True)

        if r.status_code == 200:
            # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
            r.raw.decode_content = True
            with open(jpg_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            log('Image sucessfully Downloaded: {}'.format(jpg_path))
        else:
            log('Image Couldn\'t be retreived')

    # Get and write info
    if plugin.get_setting('nfo', bool):
        plot = xbmc.getInfoLabel("ListItem.Plot")
        nfo_nfo = "Channel: {}\nTitle: {}\nStart: {} - End: {}\nPlot: {}".format(fchannelname,ftitle,local_starttime, local_endtime, plot)
        nfo_nfo += "\n\nDownloaded using IPTV Archive Downloader\nhttps://github.com/tbrek/IPTV-Archive-Downloader"
        f = xbmcvfs.File(nfo_path,'w')
        write_in_file(f,nfo_nfo)
        f.close()

    # Write JSON
    if plugin.get_setting('json', bool):
        json_nfo = json.dumps(nfo)
        f = xbmcvfs.File(json_path,'w')
        write_in_file(f, json_nfo)
        f.close()
    time_shift = int(plugin.get_setting('external.m3u.shift', str) or "0")
    utc = int(datetime2timestamp(start)  + 3600 * time_shift - before * 60)
    lutc = int(datetime2timestamp(stop)  + 3600 * time_shift + after * 60)
    # log("UTC_OFFSET: {}".format(utc_offset))
    # log("Start: {}".format(start))
    # log("Stop: {}".format(stop))
    # log("UTC: {}".format(utc))
    # log("LUTC: {}".format(lutc))
    
    lengthSeconds = lutc-utc
    partLength = int(plugin.get_setting('part.length', str) or "3600")
    log("Part length: {}s".format(partLength))
    numberOfParts = math.floor((lutc-utc)/partLength)
    log("Number of parts: {}".format(numberOfParts))
    remainingSeconds = lengthSeconds-(numberOfParts*partLength)
    log("Remaining secods: {}".format(remainingSeconds))
    xbmcgui.Dialog().notification("{}: {}".format(
        addon.getLocalizedString(30053), channelname), title, sound=True)
    # Recording hour bits
    for part in range(0, numberOfParts): 
        cmd = [ffmpeg]
        start=utc+(part*partLength)
        stop=start+partLength
        duration=partLength
        tempFilename = filename+"_"+"{}".format(part)
        cmd, ffmpeg_recording_path = getCmd(start, stop, cmd, past_recording, url, headers, ffmpeg_dir, tempFilename, duration)
        log("Command recording main parts: {}".format(cmd))
        recordSegment(cmd, ffmpeg_recording_path)        
    # Recording remaining minutes
    if remainingSeconds !=0:
        cmd = [ffmpeg]
        start = utc+(partLength * numberOfParts)
        stop = start + remainingSeconds
        tempFilename = filename+"_"+"{}".format(numberOfParts)
        cmd, ffmpeg_recording_path = getCmd(start,stop, cmd, past_recording, url, headers, ffmpeg_dir, tempFilename, remainingSeconds)
        recordSegment(cmd, ffmpeg_recording_path)
        log("Command recording remaining bit: {}".format(cmd))
        numberOfParts += 1
    # Do you want to concat it all together  
    if plugin.get_setting('join.segments', bool):
               
        # Concating fragments
        if (plugin.get_setting('output.format') == "0"): # ts
            output_format="ts"
            output_format_ffmpeg="mpegts"
        if (plugin.get_setting('output.format') == "1"): # mp4
            output_format="mp4"
            output_format_ffmpeg="mp4"
        if (plugin.get_setting('output.format') == "2"): # matroska
            output_format="mkv"
            output_format_ffmpeg="matroska"
        ffmpeg_recording_path = os.path.join(ffmpeg_dir, filename + '.' + output_format)
        log("Destination file: {}".format(ffmpeg_recording_path))
        temp_file_path = os.path.join(ffmpeg_dir, filename + '-temp.ts')
        log("Temporary file: {}".format(temp_file_path))
        tempFile = open(temp_file_path, "wb")
        for fileName in sorted(os.listdir(ffmpeg_dir)):
            if fileName.startswith(filename+"_") and fileName.endswith('ts'):
                log("Joining: {}".format(fileName))
                temp = open(ffmpeg_dir+"/"+fileName, "rb")
                # tempFile.write(temp.read())
                shutil.copyfileobj(temp, tempFile)
                temp.close()
                log("Deleting part: {}".format(fileName))
                os.remove(ffmpeg_dir+"/"+fileName)
        tempFile.close()
        cmd = [ffmpeg]
        cmd.append("-i")
        cmd.append(temp_file_path)
        probe_cmd = cmd
        cmd = probe_cmd + \
            ["-fflags", "+genpts",
             "-c:v", "copy", "-c:a", "aac", "-map","0" ]
             
        # if (plugin.get_setting('ffmpeg.pipe', str) == 'true') and not (windows() and (plugin.get_setting('task.scheduler', str) == 'true')):
        cmd = cmd + ['-f', output_format_ffmpeg, '-movflags', 'frag_keyframe+empty_moov', '-']
        # else:
        # cmd.append(ffmpeg_recording_path)
        log("Convert CMD: {}".format(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
        f = xbmcvfs.File(ffmpeg_recording_path, "w")
        f.write(bytearray(repr(p.pid).encode('utf-8')))
        f.close()
        video = xbmcvfs.File(ffmpeg_recording_path, "w")
        # playing = False
        while True:
            data = p.stdout.read(1000000)
            if data:
                video.write(bytearray(data))
            else:
                break
        video.close()
        log("Deleteing temporary file: {}".format(temp_file_path))
        os.remove(temp_file_path)
        
    os.remove(str(new_queue_file_path))
    plugin.set_setting('current.queue', '')
    xbmcgui.Dialog().notification('{}: {}'.format(
        addon.getLocalizedString(30054), channelname), title, sound=True)
    
    refresh()
    manage_queue()
    

def recordSegment(cmd, ffmpeg_recording_path):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
    f = xbmcvfs.File(ffmpeg_recording_path, 'w')
    f.write(bytearray(repr(p.pid).encode('utf-8')))
    f.close()
    video = xbmcvfs.File(ffmpeg_recording_path, 'w')
    # playing = False
    while True:
        data = p.stdout.read(1000000)
        if data:
            video.write(bytearray(data))
        else:
            break
    video.close()

def getCmd(start, stop, cmd, past_recording, url, headers, ffmpeg_dir, filename, duration):
    cmd.append('-i')
    # Load archive format
    archive_type = plugin.get_setting('external.m3u.archive', str)
    # log('Settings: {}'.format(archive_type))

    # if (plugin.get_setting('output.format') == "0"): # mkv
    #     output_format="mkv"
    # if (plugin.get_setting('output.format') == "1"): # ts
    #     output_format="ts"
    output_format="ts"
    if (plugin.get_setting('external.m3u.archive', str) == "0"): # TeleEleVidenie
        url=url+"?utc={}&lutc={}".format(start,stop)
    if (plugin.get_setting('external.m3u.archive', str) == "1"): # PlusX.tv
        legacy_url=url+"&utc={}&lutc={}".format(start,stop)
        offset = int(time.time()) - start
        url=url.replace("mono.m3u8","mono-{}-{}".format(start,duration) + ".m3u8")
        log("Stream info:")
        log("Legacy URL:{}".format(legacy_url))
        log("URL: {}".format(url))
        log("Start: {}, Stop: {}, Offset: {}".format(start,stop,offset))

        # PlusX URL Format
        # http://cdnx1.plusx.tv:4000/144/mono.m3u8?token={{token}}
        # http://cdnx1.plusx.tv:4000/138/mono-timeshift_rel-519409.m3u8?token={{token}}


    if (plugin.get_setting('external.m3u.archive', str) == "2"): # Custom
        archive_format = plugin.get_setting('external.m3u.custom', str).format(start,stop)
        url=url+archive_format
   
    cmd.append(url)
 
    for h in headers:
        cmd.append("-headers")
        cmd.append("%s:%s" % (h, headers[h]))
    # log(cmd)
    probe_cmd = cmd
    ffmpeg_recording_path = os.path.join(ffmpeg_dir, filename + '.' + output_format)
    cmd = probe_cmd + ["-y", "-t", str(duration), "-fflags","+genpts","-c:v","copy","-c:a","aac"]
    if plugin.get_setting('audio.tracks', bool):
        cmd = cmd + ['-map','0']
    ffmpeg_reconnect = plugin.get_setting('ffmpeg.reconnect', bool)
    if ffmpeg_reconnect:
        cmd = cmd + ["-reconnect_at_eof", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "300"]
    ffmpeg_args = plugin.get_setting('ffmpeg.args', str)
    if ffmpeg_args:
        cmd = cmd + ffmpeg_args.split(' ')
    if (plugin.get_setting('ffmpeg.pipe', str) == 'true') and not (windows() and (plugin.get_setting('task.scheduler', str) == 'true')):
        cmd = cmd + ['-f', 'mpegts','-']
    else:
        cmd.append(ffmpeg_recording_path)
    

    # log("Command: {}".format(cmd))
    return cmd, ffmpeg_recording_path

@plugin.route('/convert/<path>')
def convert(path):
    input = xbmcvfs.File(path,'rb')
    output = xbmcvfs.File(path.replace('.ts','.mp4'),'wb')
    error = open(xbmcvfs.translatePath("special://profile/addon_data/plugin.video.iptv.archive.downloader/errors.txt"), "w", encoding='utf-8')

    cmd = [ffmpeg_location(),"-fflags","+genpts","-y","-i","-","-vcodec","copy","-acodec","copy","-f", "mpegts", "- >>"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error, shell=windows())
    t = threading.Thread(target=read_thread,args=[p,output])
    t.start()
    while True:
        data_bytes = bytes(input.readBytes(100000))
        if not data_bytes:
            break
        p.stdin.write(bytearray(data_bytes))
    p.stdin.close()
    error.close()

def read_thread(p,output):
    while True:
        data = p.stdout.read(100000)
        if not len(data):
            break
        output.write(data)
    output.close()

def sane_name(name):
    if not name:
        return
    # if windows() or (plugin.get_setting('filename.urlencode', str) == 'true'):
        name = quote(name.encode('utf-8'))
        name = name.replace("%20",' ')
        name = name.replace(",", " -")
        name = name.replace('/', "%2F")
        name = name.replace('%2C', " -")
        name = name.replace(':', " -")
        name = name.replace("%3A", " -")
        name = name.replace("%C4%84", "A")
        name = name.replace("%C4%85", "a")
        name = name.replace("%C4%86", "C")
        name = name.replace("%C4%87", "c")
        name = name.replace("%C4%98", "E")
        name = name.replace("%C4%99", "e")
        name = name.replace("%C5%81", "L")
        name = name.replace("%C5%82", "l")
        name = name.replace("%C5%83", "N")
        name = name.replace("%C5%84", "n")
        name = name.replace("%C5%93", "O")
        name = name.replace("%C3%B3", "o")
        name = name.replace("%C5%9A", "S")
        name = name.replace("%C5%9B", "s")
        name = name.replace("%C5%B9", "Z")
        name = name.replace("%C5%BA", "z")
        name = name.replace("%C5%BB", "Z")
        name = name.replace("%C5%BC", "z")
    # else:
        # _quote = {'"': '%22', '|': '%7C', '*': '%2A', '/': '%2F', '<': '%3C', ':': '%3A', '\\': '%5C', '?': '%3F', '>': '%3E'}
        # for char in _quote:
            # name = name.replace(char, _quote[char])
    return name

def refresh():
    containerAddonName = xbmc.getInfoLabel('Container.PluginName')
    # log(containerAddonName)
    AddonName = xbmcaddon.Addon().getAddonInfo('id')
    if (containerAddonName == AddonName):
        xbmc.executebuiltin('Container.Refresh')

def datetime2timestamp(dt):
    epoch=datetime.fromtimestamp(0.0)
    td = dt - epoch
    return (td.microseconds + (td.seconds + td.days * 86400) * 10**6) / 10**6


def timestamp2datetime(ts):
    return datetime.fromtimestamp(ts)

def time2str(t):
    return "%02d:%02d" % (t.hour,t.minute)

def str2time(s):
    return datetime.time(hour=int(s[0:1],minute=int(s[3:4])))

def day(timestamp):
    if timestamp:
        today = datetime.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        if today.date() == timestamp.date():
            return get_string('Today')
        elif tomorrow.date() == timestamp.date():
            return get_string('Tomorrow')
        elif yesterday.date() == timestamp.date():
            return get_string('Yesterday')
        else:
            return get_string(timestamp.strftime("%A"))

def focus(i):

    #TODO find way to check this has worked (clist.getSelectedPosition returns -1)
    xbmc.sleep(int(plugin.get_setting('scroll.ms', str) or "0"))
    #TODO deal with hidden ..
    win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    cid = win.getFocusId()
    if cid:
        clist = win.getControl(cid)
        if clist:
            try: clist.selectItem(i)
            except: pass


@plugin.route('/service')
def service():
    threading.Thread(target=service_thread).start()


@plugin.route('/full_service')
def full_service():
    check_queued_items()
    xmltv()
    service_thread()


@plugin.route('/service_thread')
def service_thread():
    conn = sqlite3.connect(xbmcvfs.translatePath('%sxmltv.db' % plugin.addon.getAddonInfo('profile')), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cursor = conn.cursor()
    if not check_has_db_filled_show_error_message_ifn(cursor):
        return
    refresh()
    manage_queue()


def find_files(root):
    if (plugin.get_setting('output.format') == "0"): # mkv
        output_format="mkv"
    if (plugin.get_setting('output.format') == "1"): # ts
        output_format="ts"
    dirs, files = xbmcvfs.listdir(root)
    found_files = []
    for dir in dirs:
        path = os.path.join(xbmcvfs.translatePath(root), dir)
        found_files = found_files + find_files(path)
    file_list = []
    for file in files:
        if file.endswith('.' + output_format):
            file = os.path.join(xbmcvfs.translatePath(root), file)
            file_list.append(file)
    return found_files + file_list


def xml2utc(xml):
    if len(xml) == 14:
        xml = xml + " +0000"
    match = re.search(r'([0-9]{4})([0-9]{2})([0-9]{2})([0-9]{2})([0-9]{2})([0-9]{2}) ([+-])([0-9]{2})([0-9]{2})', xml)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        hour = int(match.group(4))
        minute = int(match.group(5))
        second = int(match.group(6))
        sign = match.group(7)
        hours = int(match.group(8))
        minutes = int(match.group(9))
        dt = datetime(year, month, day, hour, minute, second)
        td = timedelta(hours=hours, minutes=minutes)
        if sign == '+':
            dt = dt - td
        else:
            dt = dt + td
        return dt
    return ''

@plugin.route('/xmltv')
def xmltv():
    load_groups = plugin.get_storage('load_groups')
    load_channels = {}

    dialog = xbmcgui.DialogProgressBG()
    dialog.create("IPTV Recorder", get_string("Loading data..."))

    profilePath = xbmcvfs.translatePath(plugin.addon.getAddonInfo('profile'))
    xbmcvfs.mkdirs(profilePath)

    shifts = {}
    streams_to_insert = []

    dialog.update(0, message=get_string("Finding streams"))
    mode = plugin.get_setting('external.m3u', str)
    if mode == "0":
        try:
            path = plugin.get_setting('external.m3u.file',str)
        except:
            path = ""
    else:
        try:
            path = plugin.get_setting('external.m3u.url',str)
        except:
            path = ""

    if path:
        m3uFile = 'special://profile/addon_data/plugin.video.iptv.archive.downloader/channels.m3u'

        xbmcvfs.copy(path, m3uFile)
        f = open(xbmcvfs.translatePath(m3uFile),'rb')
        data = f.read()
        data = data.decode('utf8')
        settings_shift = float(plugin.get_setting('external.m3u.shift', str))
        global_shift = settings_shift

        header = re.search('#EXTM3U(.*)', data)
        if header:
            tvg_shift = re.search('tvg-shift="(.*?)"', header.group(1))
            if tvg_shift:
                tvg_shift = tvg_shift.group(1)
                if tvg_shift:
                    global_shift = float(tvg_shift) + settings_shift

        channels = re.findall('#EXTINF:(.*?)(?:\r\n|\r|\n)(.*?)(?:\r\n|\r|\n|$)', data, flags=(re.I | re.DOTALL))
        total = len(channels)
        i = 0
        for channel in channels:

            name = None
            if ',' in re.sub('tvg-[a-z]+"[^"]*"','',channel[0], flags=re.I):
                name = channel[0].rsplit(',', 1)[-1].strip()
                name = name.replace('+','')
                name = name.replace(':','')
                name = name.replace('#','')
                #name = name.encode("utf8")

            tvg_name = re.search('tvg-name="(.*?)"', channel[0], flags=re.I)
            if tvg_name:
                tvg_name = tvg_name.group(1) or None
            #else:
                #tvg_name = name

            tvg_id = re.search('tvg-id="(.*?)"', channel[0], flags=re.I)
            if tvg_id:
                tvg_id = tvg_id.group(1) or None

            tvg_logo = re.search('tvg-logo="(.*?)"', channel[0], flags=re.I)
            if tvg_logo:
                tvg_logo = tvg_logo.group(1) or None

            shifts[tvg_id] = global_shift
            tvg_shift = re.search('tvg-shift="(.*?)"', channel[0], flags=re.I)
            if tvg_shift:
                tvg_shift = tvg_shift.group(1)
                if tvg_shift and tvg_id:
                    shifts[tvg_id] = float(tvg_shift) + settings_shift

            url = channel[1]
            search = plugin.get_setting('m3u.regex.search', str)
            replace = plugin.get_setting('m3u.regex.replace', str)
            if search:
                url = re.sub(search, replace, url)

            groups = re.search('group-title="(.*?)"', channel[0], flags=re.I)
            if groups:
                groups = groups.group(1) or None

            streams_to_insert.append((name, tvg_name, tvg_id, tvg_logo, groups, url.strip(), i))
            i += 1
            percent = 0 + int(100.0 * i / total)
            dialog.update(percent, message=get_string("Finding streams"))


    '''
    missing_streams = conn.execute('SELECT name, tvg_name FROM streams WHERE tvg_id IS null OR tvg_id IS ""').fetchall()
    sql_channels = conn.execute('SELECT id, name FROM channels').fetchall()
    lower_channels = {x[1].lower():x[0] for x in sql_channels}
    for name, tvg_name in missing_streams:
        if tvg_name:
            tvg_id = None
            _tvg_name = tvg_name.replace("_"," ").lower()
            if _tvg_name in lower_channels:
                tvg_id = lower_channels[_tvg_name]
                conn.execute("UPDATE streams SET tvg_id=? WHERE tvg_name=?", (tvg_id, tvg_name))
        elif name.lower() in lower_channels:
            tvg_id = lower_channels[name.lower()]
            conn.execute("UPDATE streams SET tvg_id=? WHERE name=?", (tvg_id, name))
    '''
    
    for _, _, tvg_id, _, groups, _, _ in streams_to_insert:
        if groups in load_groups:
            load_channels[tvg_id] = ""
    # log("-----------------------------------------Streams----------------------")
    # log(streams_to_insert)
    # log("-------------------------------------------End------------------------")
    dialog.update(0, message=get_string("Creating database"))
    databasePath = os.path.join(profilePath, 'xmltv.db')
    conn = sqlite3.connect(databasePath, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.row_factory = sqlite3.Row
    conn.execute('DROP TABLE IF EXISTS streams')
    conn.execute('CREATE TABLE IF NOT EXISTS streams(uid INTEGER PRIMARY KEY ASC, name TEXT, tvg_name TEXT, tvg_id TEXT, tvg_logo TEXT, groups TEXT, url TEXT, tv_number INTEGER)')
  
    dialog.update(0, message=get_string("Updating database"))
    conn.executemany("INSERT OR IGNORE INTO streams(name, tvg_name, tvg_id, tvg_logo, groups, url, tv_number) VALUES (?, ?, ?, ?, ?, ?, ?)", streams_to_insert)

    # ('TVP 1 FHD', None, 'TVP 1 3', 'https://tombrek.com/setup/tv/icons/tvp1.png', None, 'https://my.teleelevidenie.com/play/hls-apple-c468-t7958e3b2ddcc16298ec0629849d3fe7738506e11ebd7f34d22e4a1acee128514.m3u8', 0)
    conn.commit()
    conn.close()

    dialog.update(100, message=get_string("Finished loading data"))
    time.sleep(1)
    dialog.close()
    return


@plugin.route('/nuke')
def nuke():

    if not (xbmcgui.Dialog().yesno("IPTV Archive Downloader", addon.getLocalizedString(30057))):
        return

    xbmcvfs.delete(xbmcvfs.translatePath('%sxmltv.db' % plugin.addon.getAddonInfo('profile')))
    time.sleep(5)
    full_service()

@plugin.route('/settings')
def settings():
    xbmcaddon.Addon().openSettings()


@plugin.route('/queue')
def queue():
    addon_data = xbmcvfs.translatePath(plugin.addon.getAddonInfo('profile'))
    queue_path = os.path.join(addon_data, 'queue')
    list_of_queue_files = glob.glob(queue_path + "/*.*")
    items = []
    if list_of_queue_files:
        items.append({
            'label': 'Delete all queued downloads',
            'path': plugin.url_for('delete_all_from_queue'),
            'thumbnail': get_icon_path('unknown'),
            'context_menu': '',
        })
    for queue_item in list_of_queue_files:
        context_items = []
        context_items.append((addon.getLocalizedString(30077), 'RunPlugin(%s)' % (plugin.url_for(delete_from_queue, queue_item=os.path.basename(queue_item)))))
        if plugin.get_setting('current.queue') == os.path.basename(queue_item):
            icon = get_icon_path('queue')
        else:
            icon = get_icon_path('recordings')
        items.append({
            'label': os.path.basename(queue_item),
            'path': plugin.url_for('queue'),
            'thumbnail': icon,
            'context_menu': context_items,
        })
    return items


@plugin.route('/delete_all_from-queue')
def delete_all_from_queue():
    if not (xbmcgui.Dialog().yesno("IPTV Archive Downloader", addon.getLocalizedString(30078))):
        return
    addon_data = xbmcvfs.translatePath(plugin.addon.getAddonInfo('profile'))
    queue_path = os.path.join(addon_data, 'queue')
    list_of_queue_files = glob.glob(queue_path + "/*.*")
    for queue_item in list_of_queue_files:
        os.remove(queue_item)
    plugin.set_setting('current.queue', '')
    refresh()


@plugin.route('/delete_from_queue/<queue_item>')
def delete_from_queue(queue_item):
    if not (xbmcgui.Dialog().yesno("IPTV Archive Downloader", addon.getLocalizedString(30075))):
        return
    addon_data = xbmcvfs.translatePath(plugin.addon.getAddonInfo('profile'))
    queue_file_path = os.path.join(addon_data, 'queue', queue_item)
    xbmcvfs.delete(queue_file_path)
    refresh()


@plugin.route('/')
def index():
    items = []
    context_items = []
    items.append(
        {
            'label': addon.getLocalizedString(30058),
            'path': plugin.get_setting('recordings', str),
            'thumbnail': get_icon_path('recordings'),
            'context_menu': context_items,
        })

    items.append(
        {
            'label': addon.getLocalizedString(30060),
            'path': plugin_url_for(plugin, 'settings'),
            'thumbnail': get_icon_path('settings'),
            'context_menu': context_items,
        })

    items.append(
        {
            'label': addon.getLocalizedString(30059),
            'path': plugin_url_for(plugin, 'nuke'),
            'thumbnail': get_icon_path('unknown'),
            'context_menu': context_items,
        })
    
    items.append(
        {
            'label': addon.getLocalizedString(30076),
            'path': plugin_url_for(plugin, 'queue'),
            'thumbnail': get_icon_path('queue'),
            'context_menu': context_items,
        })
    
    return items


if __name__ == '__main__':
    plugin.run()

    containerAddonName = xbmc.getInfoLabel('Container.PluginName')
    AddonName = xbmcaddon.Addon().getAddonInfo('id')

    if containerAddonName == AddonName:

        if big_list_view == True:

            view_mode = int(plugin.get_setting('view.mode', str) or "0")

            if view_mode:
                plugin.set_view_mode(view_mode)
