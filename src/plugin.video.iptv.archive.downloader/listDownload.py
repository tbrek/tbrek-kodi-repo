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
    fullDate = fullDate.replace('Poniedzia\u0142ek', 'Monday')
    fullDate = fullDate.replace("Wtorek", "Tuesday")
    fullDate = fullDate.replace('\u015aroda', 'Wednesday')
    fullDate = fullDate.replace('Czwartek', 'Thursday')
    fullDate = fullDate.replace('Pi\u0105tek', 'Friday')
    fullDate = fullDate.replace('Sobota', 'Saturday')
    fullDate = fullDate.replace('Niedziela', 'Sunday')
    fullDate = fullDate.replace('Stycznia', 'January')
    fullDate = fullDate.replace('Lutego', 'February')
    fullDate = fullDate.replace('Marca', 'March')
    fullDate = fullDate.replace('Kwietnia', 'April')
    fullDate = fullDate.replace('Maja', 'May')
    fullDate = fullDate.replace('Czerwca', 'June')
    fullDate = fullDate.replace('Lipca', 'July')
    fullDate = fullDate.replace('Sierpnia', 'August')
    fullDate = fullDate.replace('Wrze\u015bnia', 'September')
    fullDate = fullDate.replace('Pa\u017adziernika', 'October')
    fullDate = fullDate.replace('Listopada', 'November')
    fullDate = fullDate.replace('Grudnia', 'December')
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
