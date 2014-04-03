#!/usr/bin/env python

import sqlite3
from time import strftime
from datetime import datetime
import os

COLORS = ["#f8ff78", "#85d7ff", "cornsilk", "lightpink", "lightgreen", "yellowgreen", "lightgrey", "khaki", "mistyrose"]

TEMPLATEBEGINNING = """
<html>
<head>
<title>WhatsApp Conversation</title>
<meta charset="utf-8">
<style type="text/css">
body {
	font-family: Helvetica Neue;
}
td {
	font-size: .8em;
	max-width: 800px;
}
</style>
</head>
<body>
<table>
<thead>
<tr>
<th>Date</th>
<th>From</th>
<th>Content</th>
</tr>
</thead>
<tbody>
"""

TEMPLATEEND = """
</tbody>
</table></body>
</html>
"""

ROWTEMPLATE = """<tr style="background-color: %s"><td>%s</td><td>%s</td><td>%s</td></tr>"""

OUTPUT_DIR = "output_%s" % (strftime("%Y_%m_%d"))
if not os.path.exists(OUTPUT_DIR):
	os.makedirs(OUTPUT_DIR)
CHAT_STORAGE_FILE = os.path.join(OUTPUT_DIR, "ChatStorage.sqlite")

FIELDS = "ZFROMJID, ZTEXT, ZMESSAGEDATE, ZMESSAGETYPE, ZGROUPEVENTTYPE, ZGROUPMEMBER, ZMEDIAITEM"

cached_colors = {}
next_color = 0
def get_color(contact):
	global next_color
	if contact in cached_colors:
		return cached_colors[contact]
	cached_colors[contact] = COLORS[1:][next_color % (len(COLORS) - 1)]
	next_color += 1
	return cached_colors[contact]

cached_members = {}
def get_group_member_name(conn, id):
	if id in cached_members:
		return cached_members[id]
	c = conn.cursor()
	c.execute("SELECT ZCONTACTNAME FROM ZWAGROUPMEMBER WHERE Z_PK=?", (id,))
	cached_members[id] = next(c)[0]
	return cached_members[id]

def get_media_data(conn, mediaid, cols):
	c = conn.cursor()
	c.execute("SELECT {} FROM ZWAMEDIAITEM WHERE Z_PK=?".format(cols), (mediaid,))
	return next(c)

def get_text(conn, row):
	mfrom, mtext, mdate, mtype, mgroupeventtype, mgroupmember, mmediaitem = row
	if mtype == 0:
		return mtext
	if mtype == 6:
		if mgroupmember is None:
			mgroupmember = "you"
		else:
			mgroupmember = get_group_member_name(conn, mgroupmember)
		if mgroupeventtype == 1:
			return "[{} changed the group subject to {}]".format(mgroupmember, mtext)
		if mgroupeventtype == 2:
			return "[{} joined]".format(mgroupmember)
		if mgroupeventtype == 3:
			return "[{} left]".format(mgroupmember)
		if mgroupeventtype == 4:
			return "[{} changed the group photo]".format(mgroupmember)
		return "[group event {} by {}]".format(mgroupeventtype, mgroupmember)
	if mtype in [1, 2, 3, 4, 5]:
		mediadata = ["ZMEDIALOCALPATH", "ZMEDIALOCALPATH", "ZMEDIALOCALPATH", "ZVCARDNAME",
		             "ZLATITUDE, ZLONGITUDE"][mtype-1]
		mtype = ["image", "video", "audio", "contact", "location"][mtype-1]
		data = get_media_data(conn, mmediaitem, mediadata)
		return "[{} - data {}]".format(mtype, data)
	return "[message type %d]" % mtype

def get_from(conn, is_group, contact_id, contact_name, your_name, row):
	mfrom, mtext, mdate, mtype, mgroupeventtype, mgroupmember, mmediaitem = row
	if mfrom != contact_id:
		if is_group:
			return contact_name + " - " + your_name, COLORS[0]
		else:
			return your_name, COLORS[0]
	mfrom = contact_name
	if is_group:
		if mgroupmember is not None and mtype != 6:
			mfrom += " - " + get_group_member_name(conn, mgroupmember)
	color = get_color(mfrom)
	return mfrom, color

def get_date(mdate):
	mdatetime = datetime.fromtimestamp(int(mdate))
	mdatetime = mdatetime.replace(year=mdatetime.year + 31)
	mdatetime = mdatetime.strftime("%Y-%m-%d %H:%M:%S")
	return mdatetime

def output_contact(conn, is_group, contact_id, contact_name, your_name):
	global next_color
	next_color = 0
	html = open(os.path.join(OUTPUT_DIR, '%s.html' % contact_name), 'w', encoding="utf-8")
	html.write(TEMPLATEBEGINNING)
	c = conn.cursor()
	c.execute("SELECT COUNT(*) FROM ZWAMESSAGE WHERE ZFROMJID=? OR ZTOJID=?;", (contact_id, contact_id))
	for count in c:
		totalmessages = count[0]

	c.execute("SELECT {} FROM ZWAMESSAGE WHERE ZFROMJID=? OR ZTOJID=?;".format(FIELDS), (contact_id, contact_id))
	done = 0
	previouspercent = 0
	for row in c:
		mfrom, mtext, mdate, mtype, mgroupeventtype, mgroupmember, mmediaitem = row
		mdatetime = get_date(mdate)
		mtext = get_text(conn, row)
		mfrom, color = get_from(conn, is_group, contact_id, contact_name, your_name, row)
		html.write((ROWTEMPLATE % (color, mdatetime, mfrom, mtext)))
		done = done + 1
		percent = round(float(done)/totalmessages*100)
		if percent != previouspercent:
			bar = "[%s%s]" % ("#"*int(percent/10),"-"*(10-int(percent/10)))
			print("%s %d%% done" % (bar, percent), end="\r")
			previouspercent = percent
	print()
	html.write(TEMPLATEEND)
	html.close()

def main():
	conn = sqlite3.connect(CHAT_STORAGE_FILE)
	c = conn.cursor()
	c.execute("SELECT ZCONTACTJID, ZPARTNERNAME, ZSESSIONTYPE FROM ZWACHATSESSION")
	for contact_id, contact_name, is_group in c:
		output_contact(conn, is_group, contact_id, contact_name, "me")