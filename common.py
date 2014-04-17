from time import strftime
import os
import sys
from datetime import datetime

COLORS = ["#f8ff78", "#85d7ff", "cornsilk", "lightpink", "lightgreen", "yellowgreen", "lightgrey", "khaki", "mistyrose"]

TEMPLATEBEGINNING = """
<html>
<head>
<title>%s Conversation</title>
<meta charset="utf-8">
<style type="text/css">
body {
    font-family: "Helvetica Neue", Arial, sans-serif;
}
.main td {
    max-width: 800px;
    padding-left: 10px;
    padding-right: 10px;
    border-bottom: 5px solid #fff;
}
.main td:first-child {
    white-space: nowrap;
    color: #666;
    font-size: 13px;
}
</style>
</head>
<body>
<table class="main" cellpadding="0" cellspacing="0">
<tbody>
"""

TEMPLATEEND = """
</tbody>
</table></body>
</html>
"""

ROWTEMPLATE = """<tr style="background-color: %s"><td>%s</td><td>%s</td><td>%s</td></tr>\n"""

def get_output_dirs(name):
	OUTPUT_DIR = "output_%s_%s" % (strftime("%Y_%m_%d"), name)
	MEDIA_DIR = os.path.join(OUTPUT_DIR, "media")
	if not os.path.exists(MEDIA_DIR):
		os.makedirs(MEDIA_DIR)
	return OUTPUT_DIR, MEDIA_DIR

cached_colors = {}
next_color = 0
def get_color(contact):
	global next_color
	if contact in cached_colors:
		return cached_colors[contact]
	cached_colors[contact] = COLORS[1:][next_color % (len(COLORS) - 1)]
	next_color += 1
	return cached_colors[contact]

def reset_colors():
	global next_color, cached_colors
	cached_colors = {}
	next_color = 0

def get_date(mdate):
	mdatetime = datetime.fromtimestamp(int(mdate))
	mdatetime = mdatetime.replace(year=mdatetime.year + 31)
	mdatetime = mdatetime.strftime("%Y-%m-%d %H:%M:%S")
	return mdatetime

def sanitize_filename(f):
	invalid_chars = "?*/\\:\"<>|"
	for char in invalid_chars:
		f = f.replace(char, "-")
	return f

def iterate_with_progress(iterator, count, name):
	previouspercent = 0
	for index, value in enumerate(iterator):
		yield value
		percent = round((float(index+1) / count*100))
		if percent != previouspercent:
			bar = "[%s%s]" % ("#"*int(percent/10),"-"*(10-int(percent/10)))
			print("{:10s} {} {}% done".format(name, bar, percent), end="\r")
			sys.stdout.flush()
			previouspercent = percent
	print()

