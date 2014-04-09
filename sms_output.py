# TODO getting phone numbers from addressbook is israel-specific and weird
# TODO support groups - using chat_message_join and chat_handle_join db db
# TODO support atttachments - using message_attachment_join in db

import sqlite3
import os

from chat_output import iterate_with_progress, TEMPLATEBEGINNING, TEMPLATEEND, ROWTEMPLATE, OUTPUT_DIR
from chat_output import COLORS, sanitize_filename, get_date

CHAT_STORAGE_FILE = os.path.join(OUTPUT_DIR, "sms.db")
CONTACT_FILE = os.path.join(OUTPUT_DIR, "AddressBook.sqlitedb")

FIELDS = "text, date, is_from_me"

def output_contact(conn, backup_extractor, contact_id, contact_name, your_name):
	html = open(os.path.join(OUTPUT_DIR, '%s.html' % sanitize_filename(contact_name)), 'w', encoding="utf-8")
	html.write(TEMPLATEBEGINNING % ("SMS/iMessage",))
	c = conn.cursor()
	c.execute("SELECT {} FROM message WHERE handle_id=?;".format(FIELDS), (contact_id,))
	for row in c:
		mtext, mdate, is_from_me = row
		mdatetime = get_date(mdate)
		mfrom = your_name if is_from_me else contact_name
		color = COLORS[not is_from_me]
		html.write((ROWTEMPLATE % (color, mdatetime, mfrom, mtext)))
	html.write(TEMPLATEEND)
	html.close()

def get_contact_name(conn, contact_conn, contact_id):
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
			return " ".join((s for s in next(c2) if s))
	return handle_id

def main(backup_extractor):
	contact_conn = sqlite3.connect(CONTACT_FILE)
	conn = sqlite3.connect(CHAT_STORAGE_FILE)
	c = conn.cursor()
	c.execute("SELECT COUNT(*) FROM handle")
	total_contacts = next(c)[0]
	c = conn.cursor()
	c.execute("SELECT ROWID FROM handle")
	for contact_id in iterate_with_progress(c, total_contacts):
		contact_id = str(contact_id[0])
		contact_name = get_contact_name(conn, contact_conn, contact_id)
		output_contact(conn, backup_extractor, contact_id, contact_name, "me")