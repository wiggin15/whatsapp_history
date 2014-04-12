import sqlite3
import os
import shutil
import codecs

from common import COLORS, TEMPLATEBEGINNING, TEMPLATEEND, ROWTEMPLATE, OUTPUT_DIR, MEDIA_DIR
from common import get_color, reset_colors, get_date, sanitize_filename, iterate_with_progress

CHAT_STORAGE_FILE = os.path.join(OUTPUT_DIR, "ChatStorage.sqlite")
FILES = [("AppDomain-net.whatsapp.WhatsApp", "Documents/ChatStorage.sqlite", CHAT_STORAGE_FILE)]

FIELDS = "ZFROMJID, ZTEXT, ZMESSAGEDATE, ZMESSAGETYPE, ZGROUPEVENTTYPE, ZGROUPMEMBER, ZMEDIAITEM"

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

def handle_media(conn, backup_extractor, mtype, mmediaitem):
	mediadata = ["ZMEDIALOCALPATH", "ZMEDIALOCALPATH", "ZMEDIALOCALPATH", "ZVCARDNAME",
	             "ZLATITUDE, ZLONGITUDE"][mtype-1]
	data = get_media_data(conn, mmediaitem, mediadata)
	mtypestr = {1: "image", 2: "video", 3: "audio", 4: "contact", 5: "location"}[mtype]
	if data[0] is None:
		return "[missing {}]".format(mtypestr)
	data = ", ".join([str(x) for x in data])
	if mtype in [1, 2, 3]:
		data = "Library" + ("" if data.startswith("/") else "/") + data
		filepath = backup_extractor.get_file_path("AppDomain-net.whatsapp.WhatsApp", data)
		new_media_path = os.path.join(MEDIA_DIR, os.path.basename(data))
		shutil.copy(filepath, new_media_path)
		tag_format = '<a href="media/{1}"><{0} src="media/{1}" style="width:200px;"{2}></a>'
		tag = ["img", "video", "audio"][mtype-1]
		controls = " controls" if tag in ["audio", "video"] else ""
		return tag_format.format(tag, os.path.basename(new_media_path), controls)
	if mtype == 4 and data.startswith("="):
		# if the vCard has no contact image the format of the row in the db is a little different,
		# and name is encoded using quopri encoding
		try:
			data = str(codecs.decode(bytes(data, "ascii"), "quopri"), "utf-8")
		except:
			pass
	return "[{} - {}]".format(mtypestr, data)

def get_text(conn, backup_extractor, row):
	mfrom, mtext, mdate, mtype, mgroupeventtype, mgroupmember, mmediaitem = row
	if mtype == 0:
		return mtext
	if mtype == 6:
		mgroupmember = "you" if mgroupmember is None else get_group_member_name(conn, mgroupmember)
		if mgroupeventtype not in [1, 2, 3, 4]:
			return "[group event {} by {}]".format(mgroupeventtype, mgroupmember)
		change_text = {1: "changed the group subject to {}".format(mtext),
		               2: "joined", 3: "left", 4: "changed the group photo"}
		return "[{} {}]".format(mgroupmember, change_text[mgroupeventtype])
	if mtype in [1, 2, 3, 4, 5]:
		return handle_media(conn, backup_extractor, mtype, mmediaitem)
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

def output_contact(conn, backup_extractor, is_group, contact_id, contact_name, your_name):
	reset_colors()
	html = open(os.path.join(OUTPUT_DIR, '%s.html' % sanitize_filename(contact_name)), 'w', encoding="utf-8")
	html.write(TEMPLATEBEGINNING % ("WhatsApp",))
	c = conn.cursor()
	c.execute("SELECT {} FROM ZWAMESSAGE WHERE ZFROMJID=? OR ZTOJID=?;".format(FIELDS), (contact_id, contact_id))
	for row in c:
		mdatetime = get_date(row[2])
		mtext = get_text(conn, backup_extractor, row)
		mfrom, color = get_from(conn, is_group, contact_id, contact_name, your_name, row)
		html.write((ROWTEMPLATE % (color, mdatetime, mfrom, mtext)))
	html.write(TEMPLATEEND)
	html.close()

def main(backup_extractor):
	conn = sqlite3.connect(CHAT_STORAGE_FILE)
	c = conn.cursor()
	c.execute("SELECT COUNT(*) FROM ZWACHATSESSION")
	total_contacts = next(c)[0]
	c = conn.cursor()
	c.execute("SELECT ZCONTACTJID, ZPARTNERNAME, ZSESSIONTYPE FROM ZWACHATSESSION")
	for contact_id, contact_name, is_group in iterate_with_progress(c, total_contacts):
		output_contact(conn, backup_extractor, is_group, contact_id, contact_name, "me")
