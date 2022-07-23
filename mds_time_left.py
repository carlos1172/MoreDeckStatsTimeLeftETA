# -*- coding: utf-8 -*-
#Copyright(C)   | Carlos Duarte
#Based 1 on     | Dmitry Mikheev code, in add-on "More decks overview stats"
#Based 2 on     | calumkscode, in add-on https://github.com/calumks/anki-deck-stats
#License        | GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#Source in      | https://github.com/cjdduarte/MDS_Time_Left

import anki
from anki.lang import _, ngettext
import aqt
from aqt import mw, theme
from aqt.utils import tooltip
from aqt.overview import Overview, OverviewContent, OverviewBottomBar

import math
from datetime import datetime, timezone, timedelta, date
import time

#-------------Configuration------------------
config = mw.addonManager.getConfig(__name__)
# The default steps for "New" Anki cards are 1min and 10min meaning that you see New cards actually a minimum of *TWO* times that day
# You can now configure how many times new cards will be counted.
# CountTimesNew = 1 (old version)
# Quantify '1' time the "new card" time | Example: Steps (10 1440)
# CountTimesNew = 2 (default)
# Quantify '2' times the "new card" time | Example: Steps (1 10)
# CountTimesNew = n
# Quantify 'n' times the "new card" time | Example: Steps (1 10 10 20 30...)
CountTimesNew = config['CountTimesNew']
lrnSteps = 3
showDebug = 0
#-------------Configuration------------------

def renderStats(self, _old):
    x = (mw.col.sched.day_cutoff - 86400*7)*1000

    """Calculate progress using weights and card counts from the sched."""
    # Get studdied cards  and true retention stats
    xcards, xfailed, xdistinct, xflunked, xpassed = mw.col.db.first("""
    select
    sum(case when ease >=1 then 1 else 0 end), /* xcards */
    sum(case when ease = 1 then 1 else 0 end), /* xfailed */
    count(distinct cid), /* xdistinct */
    sum(case when ease = 1 and type == 1 then 1 else 0 end), /* xflunked */
    sum(case when ease > 1 and type == 1 then 1 else 0 end) /* xpassed */
    from revlog where id > ?""",x)
    xcards = xcards or 0
    xfailed = xfailed or 0
    xdistinct = xdistinct or 0
    xflunked = xflunked or 0
    xpassed = xpassed or 0

    TR = 1-float(xpassed/(float(max(1,xpassed+xflunked))))
    xagain = float((xfailed)/max(1,(xcards-xpassed)))
    lrnWeight = float((1+(1*xagain*lrnSteps))/1)
    newWeight = float((1+(1*xagain*lrnSteps))/1)
    revWeight = float((1+(1*TR*lrnSteps))/1)
    
    # Get due and new cards
    new = 0
    lrn = 0
    due = 0

    for tree in self.mw.col.sched.deckDueTree():
        new += tree[4]
        lrn += tree[3]
        due += tree[2]

    #if CountTimesNew == 0: CountTimesNew = 2
    total = (newWeight*new) + (lrnWeight*lrn) + (revWeight*due)
    totalDisplay = int((newWeight*new) + (lrnWeight*lrn) + (revWeight*due))
    #total = new + lrn + due

    # Get studdied cards
    cards, thetime = self.mw.col.db.first(
            """select count(), sum(time)/1000 from revlog where id > ?""",
            (self.mw.col.sched.dayCutoff - 86400) * 1000)

    cards   = cards or 0
    thetime = thetime or 0

    speed   = thetime / max(1, cards)
    minutes = (total*speed)/3600
    
    hrhr = math.floor(minutes)
    hrmin = math.floor(60*(minutes-hrhr))
    hrsec = ((minutes-hrhr)*60-hrmin)*60

    dt=datetime.today()
    tz = 8 #GMT+ <CHANGE THIS TO YOUR GMT+_ (negative number if you're GMT-)>
    tzsec = tz*3600

    t = timedelta(hours = hrhr, minutes = hrmin, seconds = hrsec)
    left = dt.timestamp()+tzsec+t.total_seconds()

    date_time = datetime.utcfromtimestamp(left).strftime('%Y-%m-%d %H:%M:%S')
    date_time_24H = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
    ETA = date_time_24H.strftime("%I:%M %p")

    if theme.theme_manager.night_mode:
        NewColor        = config['NewColorDark']
        ReviewColor     = config['ReviewColorDark']
        LearnColor      = config['LearnColorDark']
        TotalDueColor   = config['TotalDueColorDark']
        TotalColor      = config['TotalColorDark']
    else:
        NewColor        = config['NewColorLight']
        ReviewColor     = config['ReviewColorLight']
        LearnColor      = config['LearnColorLight']
        TotalDueColor   = config['TotalDueColorLight']
        TotalColor      = config['TotalColorLight']

    insert_style = "<style type=\"text/css\">" \
        + ".new-color { color:"         + NewColor + ";}" \
        + ".review-color { color:"      + ReviewColor + ";}" \
        + ".learn-color { color:"       + LearnColor + ";}" \
        + ".totaldue-color { color:"    + TotalDueColor + ";}" \
        + ".total-color { color:"       + TotalColor + ";}" \
        + "</style>"
    if showDebug:
        buf = insert_style \
        + "<div style='display:table;padding-top:1.5em;'>" \
        + "<div style='display:table-cell;'> " \
        + _old(self) + "<hr>" \
        + _("New Cards") \
        + ": &nbsp; <span class='new-color'> %(d)s</span>" % dict(d=new) \
        + " &nbsp; " + _("Learn") \
        + ": &nbsp; <span class='learn-color'>%(c)s</span>" % dict(c=lrn) \
        + " &nbsp; <span style='white-space:nowrap;'>" + _("To Review") \
        + ": &nbsp; <span class='review-color'>%(c)s</span>" % dict(c=due) \
        + "</span>" \
        + " &nbsp; <br><span style='white-space:nowrap;'>" + _("Due") \
        + ": &nbsp; <b class='totaldue-color'>%(c)s</b> " % dict(c=(lrn+due)) \
        + "</span> " \
        + " &nbsp; <span style='white-space:nowrap;'>" + _("Total") \
        + ": &nbsp; <b class='total-color'>%(c)s</b>" % dict(c=(totalDisplay)) \
        + "</span></div>" \
        + "<div style='display:table-cell;vertical-align:middle;" \
        + "padding-left:2em;'>" \
        + "<span style='white-space:nowrap;'>" + _("Statistics") \
        + ": <br>" + _("%.02f") % (speed) + "&nbsp;" + (_("s") + "/" + _("card, ").replace("s", "s")).lower()  \
        + "</span>" \
        + str(ngettext("%.02f hours", "%.02f hours", minutes) % (minutes)).replace(".", ".") + "&nbsp;" + _("More, ").lower() \
        + "</span><br>" \
        + str(ngettext("ETA %s","ETA %s",ETA) % (ETA)).replace(".",".")+ "&nbsp;" \
        + "</span><br>" \
        + str(ngettext("New/Lrn: %.02f","New/Lrn: %.02f",lrnWeight) % (lrnWeight)).replace(".",".")+ "&nbsp;" \
        + str(ngettext("Rev: %.02f","Rev: %.02f",revWeight) % (revWeight)).replace(".",".")+ "&nbsp;" \
        + "</div></div>"
    else:
        buf = insert_style \
        + "<div style='display:table;padding-top:1.5em;'>" \
        + "<div style='display:table-cell;'> " \
        + _old(self) + "<hr>" \
        + _("New Cards") \
        + ": &nbsp; <span class='new-color'> %(d)s</span>" % dict(d=new) \
        + " &nbsp; " + _("Learn") \
        + ": &nbsp; <span class='learn-color'>%(c)s</span>" % dict(c=lrn) \
        + " &nbsp; <span style='white-space:nowrap;'>" + _("To Review") \
        + ": &nbsp; <span class='review-color'>%(c)s</span>" % dict(c=due) \
        + "</span>" \
        + " &nbsp; <br><span style='white-space:nowrap;'>" + _("Due") \
        + ": &nbsp; <b class='totaldue-color'>%(c)s</b> " % dict(c=(lrn+due)) \
        + "</span> " \
        + " &nbsp; <span style='white-space:nowrap;'>" + _("Total") \
        + ": &nbsp; <b class='total-color'>%(c)s</b>" % dict(c=(totalDisplay)) \
        + "</span></div>" \
        + "<div style='display:table-cell;vertical-align:middle;" \
        + "padding-left:2em;'>" \
        + "<span style='white-space:nowrap;'>" + _("Average") \
        + ":<br> " + _("%.02f") % (speed) + "&nbsp;" + (_("s") + "/" + _("card").replace("s", "s")).lower()  \
        + "</span><br>" \
        + str(ngettext("%02d", "%02d", hrhr) % (hrhr)) + ":" + str(ngettext("%02d", "%02d", hrmin) % (hrmin)) + _(" More").lower() \
        + "</span><br>" \
        + str(ngettext("ETA %s","ETA %s",ETA) % (ETA)).replace(".",".")+ "&nbsp;" \
        + "</div></div>"
        
    return buf
        #+ ":<br> " + _("%.01f cards/minute") % (speed) \
        #+ _("More") + "&nbsp;" + ngettext("%s minute.", "%s minutes.", minutes) % (minutes) \

aqt.deckbrowser.DeckBrowser._renderStats = anki.hooks.wrap(
    aqt.deckbrowser.DeckBrowser._renderStats, renderStats, 'around')