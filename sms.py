import sqlite3
import os
import shutil

from common import COLORS, TEMPLATEBEGINNING, TEMPLATEEND, ROWTEMPLATE
from common import get_color, reset_colors, get_date, sanitize_filename, iterate_with_progress, get_output_dirs

OUTPUT_DIR, MEDIA_DIR = get_output_dirs("sms")

CHAT_STORAGE_FILE = os.path.join(OUTPUT_DIR, "sms.db")
CONTACTS_FILE = os.path.join(OUTPUT_DIR, "AddressBook.sqlitedb")

FILES = [("HomeDomain", "Library/SMS/sms.db", CHAT_STORAGE_FILE),
         ("HomeDomain", "Library/AddressBook/AddressBook.sqlitedb", CONTACTS_FILE)]

FIELDS = "ROWID, text, date, is_from_me, handle_id, cache_has_attachments"

OBJ_MARKER = "\ufffc"

contact_cache = {}
def get_contact_name(conn, contact_conn, contact_id):
	if contact_id in contact_cache:
		return contact_cache[contact_id]
	c = conn.cursor()
	c.execute("SELECT id FROM handle WHERE ROWID=?;", (contact_id,))
	handle_id = next(c)[0]		# this is either a phone number or an iMessage address
	if handle_id.startswith("+"):
		c = contact_conn.cursor()
		p = handle_id.replace("+972", "0")
		phone_options = (handle_id, p,
			"{}-{}-{}".format(p[-10:-7], p[-7:-4], p[-4:]),
			"({}) {} {}".format(p[-10:-7], p[-7:-4], p[-4:]))
		c.execute("SELECT record_id FROM ABMultiValue WHERE value=? or value=? or value=? or value=?", phone_options)
		for i in c:
			c2 = contact_conn.cursor()
			c2.execute("SELECT first, last FROM ABPerson WHERE ROWID=?", i)
			handle_id = " ".join((s for s in next(c2) if s))
	contact_cache[contact_id] = handle_id
	return handle_id

def copy_media_file(backup_extractor, path_in_backup):
	if path_in_backup.startswith("/var/mobile/"):
		path_in_backup = path_in_backup[12:]
	elif path_in_backup.startswith("~/"):
		path_in_backup = path_in_backup[2:]
	filepath = backup_extractor.get_file_path("MediaDomain", path_in_backup)
	new_media_path = os.path.join(MEDIA_DIR, os.path.basename(path_in_backup))
	shutil.copy(filepath, new_media_path)
	return new_media_path

def handle_media(conn, backup_extractor, message_id, mtext):
	c = conn.cursor()
	c.execute("SELECT filename, mime_type FROM attachment WHERE ROWID in "\
		      "(SELECT attachment_id FROM message_attachment_join WHERE message_id=?);", (message_id,))
	if mtext is None:
		mtext = ""
	for row in c:
		new_media_path = copy_media_file(backup_extractor, row[0])
		tag_format = '<a href="media/{1}"><{0} src="media/{1}" style="width:200px;"{2}></a>'
		media_type = row[1].split("/")[0]
		tag = {"video": "video", "image": "img"}.get(media_type, None)
		if tag is None:
			media_element = "[unknown attachment type: {}]".format(media_type)
		else:
			controls = " controls" if tag in ["audio", "video"] else ""
			media_element = tag_format.format(tag, os.path.basename(new_media_path), controls)
		if OBJ_MARKER in mtext:
			mtext = mtext.replace(OBJ_MARKER, media_element, 1)
		else:
			mtext = mtext + media_element
	return mtext

def get_filename(conn, contact_conn, chat_id):
	c = conn.cursor()
	c.execute("SELECT handle_id FROM chat_handle_join WHERE chat_id=?;", (chat_id,))
	names_in_chat = []
	for row in c:
		names_in_chat.append(get_contact_name(conn, contact_conn, row[0]))
	filename = sanitize_filename(" & ".join(names_in_chat))
	filename = os.path.join(OUTPUT_DIR, '%s.html' % filename)
	return filename

def output_contact(conn, contact_conn, backup_extractor, chat_id, your_name):
	reset_colors()
	contact_name = str(chat_id)
	html = open(get_filename(conn, contact_conn, chat_id), 'w', encoding="utf-8")
	html.write(TEMPLATEBEGINNING % ("SMS/iMessage",))
	c = conn.cursor()
	c.execute("SELECT {} FROM message WHERE ROWID in ".format(FIELDS) + \
		      "(SELECT message_id FROM chat_message_join WHERE chat_id=?);", (chat_id,))
	for row in c:
		mid, mtext, mdate, is_from_me, handle_id, has_attachment = row
		if has_attachment:
			mtext = handle_media(conn, backup_extractor, mid, mtext)
		mtext = mtext.replace("\n", "<br>\n")
		mdatetime = get_date(mdate)
		mfrom = your_name if is_from_me else get_contact_name(conn, contact_conn, handle_id)
		color = COLORS[0] if is_from_me else get_color(handle_id)
		html.write((ROWTEMPLATE % (color, mdatetime, mfrom, mtext)))
	html.write(TEMPLATEEND)
	html.close()

def main(backup_extractor):
	contact_conn = sqlite3.connect(CONTACTS_FILE)
	conn = sqlite3.connect(CHAT_STORAGE_FILE)
	c = conn.cursor()
	c.execute("SELECT COUNT(*) FROM chat")
	total_contacts = next(c)[0]
	c = conn.cursor()
	c.execute("SELECT ROWID FROM chat")
	for chat_id in iterate_with_progress(c, total_contacts, "SMS"):
		output_contact(conn, contact_conn, backup_extractor, chat_id[0], "me")
