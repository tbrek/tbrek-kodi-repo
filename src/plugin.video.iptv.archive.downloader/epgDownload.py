from __future__ import unicode_literals

import locale
import time
from datetime import datetime
from dateutil import parser
from kodi_six import xbmc, xbmcgui, xbmcaddon

DATE_FORMAT = "%Y-%m-%d %H:%M:00"
addon = xbmcaddon.Addon()

def log(x):
    xbmc.log(repr(x), xbmc.LOGERROR)

def get_format():
    dateFormat = xbmc.getRegion('datelong')
    timeFormat = xbmc.getRegion('time').replace('%H%H', '%H').replace('%I%I', '%I')
    timeFormat = timeFormat.replace(":%S", "")
    return "{}, {}".format(dateFormat, timeFormat)

def extract_date(dateLabel, timeLabel):
    date = xbmc.getInfoLabel(dateLabel)
    dateNew = saneDate(date)
    timeString = xbmc.getInfoLabel(timeLabel)
    fullDate = "{}, {}".format(dateNew, timeString)
    parsedDate = parser.parse(fullDate)
    return datetime.strftime(parsedDate, DATE_FORMAT)

def saneDate(fullDate):
    lookup_table = {
        "stycznia": "January",                  "Stycznia": "January",
        "lutego": "February",                   "Lutego": "February",
        "marca": "March",                       "Marca": "March",
        "kwietnia": "April",                    "Kwietnia": "April",
        "maja": "May",                          "Maja": "May", 
        "czerwca": "June",                      "Czerwca": "June",
        "lipca": "July",                        "Lipca": "July", 
        "sierpnia": "August",                   "Sierpnia": "August",
        "wrze\u015bnia": "September",           "Wrze\u015bnia": "September",
        "pa\u017adziernika": "October",         "Pa\u017adziernika": "October",
        "listopada": "November",                "Listopada": "November",
        "grudnia": "December",                  "Grudnia": "December",
        "poniedzia\u0142ek" : "Monday",         "Poniedzia\u0142ek" : "Monday", 
        "wtorek" : "Tuesday",                   "Wtorek" : "Tuesday",
        "\u015aroda": "Wednesday",              "\u015broda": "Wednesday", 
        "czwartek" : "Thursday",                "Czwartek" : "Thursday",
        "pi\u0105tek" : "Friday",               "Pi\u0105tek" : "Friday", 
        "sobota" : "Saturday",                  "Sobota" : "Saturday",
        "niedziela" : "Sunday",                 "Niedziela" : "Sunday",
    }

    for k, v in lookup_table.items():
        fullDate = fullDate.replace(k, v)
    return fullDate

fullFormat = get_format()

channel = xbmc.getInfoLabel("ListItem.ChannelName")
title = xbmc.getInfoLabel("ListItem.Label")
genre = xbmc.getInfoLabel("ListItem.Genre")
start = extract_date("ListItem.StartDate", "ListItem.StartTime")
stop = extract_date("ListItem.EndDate", "ListItem.EndTime")
channel = channel.replace('+','')
channel = channel.replace("#", '')
channel = channel.replace(":", '')
season = xbmc.getInfoLabel("ListItem.Season")
episode = xbmc.getInfoLabel("ListItem.Episode")
episode_name = xbmc.getInfoLabel("ListItem.EpisodeName")

if season != "":
    title += " - S{}".format(season)
else:
    title += " "
if episode != "" and season != "":
    title += "E{}".format(episode)
elif episode != "":
    title += " - E{}".format(episode)
if episode_name != "":
    title += " - {}".format(episode_name)

title = title.replace(" / \u2460+", "")
title = title.replace(" / \u2461+", "")
title = title.replace(" / \u2462+", "")
title = title.replace(" / \u2463+", "")
title = title.replace(" / \u2464+", "")
title = title.replace(" / \u2465+", "")
title = title.replace(" / \u2466+", "")
title = title.replace(" / \u2467+", "")
title = title.replace(" / \u2468+", "")
title = title.replace(" / \u2469+", "")
title = title.replace(" / \u246a+", "")
title = title.replace(" / \u246b+", "")
title = title.replace(" / \u246c+", "")
title = title.replace(" / \u246d+", "")
title = title.replace(" / \u246e+", "")
title = title.replace(" / \u246f+", "")
title = title.replace(" / \u2470+", "")
title = title.replace(" / \u2471+", "")
title = title.replace(" / \u2472+", "")
title = title.replace(" / \u2473+", "")

title = title.replace("%20", ' ')
title = title.replace(",", " -")
title = title.replace('/', '-')
title = title.replace('?', '')
title = title.replace('*', '')
title = title.replace('%2C', " -")
title = title.replace(':', " -")
title = title.replace("%3A", " -")
title = title.replace("\u0104", "A")
title = title.replace("\u0105", "a")
title = title.replace("\u0106", "C")
title = title.replace("\u0107", "c")
title = title.replace("\u0118", "E")
title = title.replace("\u0119", "e")
title = title.replace("\u0141", "L")
title = title.replace("\u0142", "l")
title = title.replace("\u0143", "N")
title = title.replace("\u0144", "n")
title = title.replace("\u00f2", "O")
title = title.replace("\u00f3", "o")
title = title.replace("\u015a", "S")
title = title.replace("\u015b", "s")
title = title.replace("\u0179", "Z")
title = title.replace("\u017c", "z")
title = title.replace("\u017b", "Z")
title = title.replace("\u017a", "z")


# start = extract_date("ListItem.StartDate", "ListItem.StartTime")
# stop = extract_date("ListItem.EndDate", "ListItem.EndTime")
# log("Start: {}".format(start))
# log("Stop: {}".format(stop))
    

try:
    start = extract_date("ListItem.StartDate", "ListItem.StartTime")
    stop = extract_date("ListItem.EndDate", "ListItem.EndTime") 
    try:
        cmd = "PlayMedia(plugin://plugin.video.iptv.archive.downloader/record_epg/%s/%s/%s/%s)" % (channel,
                                                                                        title,
                                                                                        start,
                                                                                        stop)
        xbmc.executebuiltin(cmd)

        message = "{}: {} ({} to {})'".format(xbmc.getInfoLabel("ListItem.ChannelName"), xbmc.getInfoLabel("ListItem.Label"), start, stop)
    except:
        xbmcgui.Dialog().notification("IPTV Archive Downloader",
                                      addon.getLocalizedString(30067), xbmcgui.NOTIFICATION_WARNING)
except Exception as e:
    xbmcgui.Dialog().notification("IPTV Archive Downloader",
                                  addon.getLocalizedString(30068), xbmcgui.NOTIFICATION_ERROR)
    log("IPTV Archive Downloader: Error parsing dates ({})".format(e))
