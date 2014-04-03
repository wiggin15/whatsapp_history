#!/usr/bin/env python

import sqlite3
from time import strftime
from datetime import datetime

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
}
.me {
	background-color: #f8ff78;
}
.other {
	background-color: #85d7ff;
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

ROWTEMPLATE = """<tr class="%s"><td>%s</td><td>%s</td><td>%s</td></tr>"""

CHAT_STORAGE_FILE = "./ChatStorage.sqlite"

def output_contact(conn, contact_id, contact_name, your_name):
	html = open('%s.html' % contact_name, 'w', encoding="utf-8")
	html.write(TEMPLATEBEGINNING)
	c = conn.cursor()
	c.execute("SELECT COUNT(*) FROM ZWAMESSAGE WHERE ZFROMJID=? OR ZTOJID=?;", (contact_id, contact_id))
	for count in c:
		totalmessages = count[0]

	c.execute("SELECT ZFROMJID, ZTEXT, ZMESSAGEDATE FROM ZWAMESSAGE WHERE ZFROMJID=? OR ZTOJID=?;", (contact_id, contact_id))
	done = 0
	previouspercent = 0
	for row in c:
		mdatetime = datetime.fromtimestamp(int(row[2]))
		mdatetime = mdatetime.replace(year=mdatetime.year + 31)
		mdatetime = mdatetime.strftime("%Y-%m-%d %H:%M:%S")
		mfrom = row[0]
		me = False
		if mfrom == contact_id:
			mfrom = contact_name
		else:
			mfrom = your_name
			me = True
		mtext = row[1]
		css_class = ('me' if me else 'other')
		html.write((ROWTEMPLATE % (css_class,mdatetime, mfrom, mtext)))
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
	c.execute("SELECT ZCONTACTJID, ZPARTNERNAME FROM ZWACHATSESSION")
	for contact_id, contact_name in c:
		output_contact(conn, contact_id, contact_name, "me")