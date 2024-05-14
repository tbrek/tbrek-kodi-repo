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
        "de Enero de": "January",
        "de Febrero de": "February",
        "de Marzo de": "March",
        "de Abril de": "April",
        "de Mayo de": "May",
        "de Junio de": "June",
        "de Julio de": "July",
        "de Agosto de": "August",
        "de Septiembre de": "Semptember",
        "de Octubre de": "October",
        "de Noviembre de": "November",
        "de Diciembre de": "December",
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
        "lunes" : "Monday",                     "Lunes" : "Monday",
        "martes" : "Tuesday",                   "Martes" : "Tuesday",
        "mi\u00e9rcoles" : "Wednesday",         "Mi\u00e9rcoles" : "Wednesday",
        "jueves" : "Thursday",                  "Jueves" : "Thursday",
        "viernes" : "Friday",                   "Viernes" : "Friday",
        "s\u00e1bado" : "Saturday",             "S\u00e1bado" : "Saturday",
        "domingo" : "Sunday",                   "Domingo" : "Sunday"
    }

    for k, v in lookup_table.items():
        fullDate = fullDate.replace(k, v)
    return fullDate

fullFormat = get_format()
dialog = xbmcgui.Dialog()
start_date = dialog.input("Start date", type=xbmcgui.INPUT_DATE)
start_time = dialog.input(
    addon.getLocalizedString(30065), type=xbmcgui.INPUT_TIME)
end_date = dialog.input("End date", type=xbmcgui.INPUT_DATE)
end_time = dialog.input(addon.getLocalizedString(30066),
                        type=xbmcgui.INPUT_TIME)


channel = xbmc.getInfoLabel("ListItem.ChannelName")
channel = channel.replace('+', '')
channel = channel.replace("#", '')
channel = channel.replace(":", '')
title = 'Recording'

yes_no = dialog.yesno(addon.getLocalizedString(30063), '{}: {} - {} to {} - {}'.format(addon.getLocalizedString(30064), start_date, start_time, end_date, end_time))

fullStartDate = "{}, {}".format(start_date, start_time)
fullEndDate = "{}, {}".format(end_date, end_time)
start = datetime.strftime(parser.parse(fullStartDate, dayfirst=True), DATE_FORMAT)
stop = datetime.strftime(parser.parse(fullEndDate, dayfirst=True), DATE_FORMAT)


if (yes_no == 1):
    try:
        log("Start: {}, End: {}".format(start, stop))
        try:
            cmd = "PlayMedia(plugin://plugin.video.iptv.archive.downloader/record_epg/%s/%s/%s/%s)" % (channel,
                                                                                                   title,
                                                                                                   start,
                                                                                                   stop)
            xbmc.executebuiltin(cmd)

            message = "{}: {} ({} to {})'".format(xbmc.getInfoLabel(
            "ListItem.ChannelName"), xbmc.getInfoLabel("ListItem.Label"), start, stop)
        except:
            xbmcgui.Dialog().notification("IPTV Archive Downloader",
                                          addon.getLocalizedString(30067), xbmcgui.NOTIFICATION_WARNING)
    except Exception as e:
        xbmcgui.Dialog().notification("IPTV Archive Downloader",
                                      addon.getLocalizedString(30068), xbmcgui.NOTIFICATION_ERROR)
        log("IPTV Archive Downloader: Error parsing dates ({})".format(e))
