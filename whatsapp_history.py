#!/usr/bin/env python

import os
import shutil
import sys
import re
import datetime
import mbdb
import chat_output
import sms_output as sms_output

class BackupExtractor():
	def _backup_time(self, backup_dir):
		# time of backup is stored in info.plist, which is in xml format
		info_file = os.path.join(backup_dir, "Info.plist")
		info_data = open(info_file, "r").read()
		match_obj = re.search("<date>(.*?)</date>", info_data)
		if match_obj is None:
			print("Could not find date of backup from %s" % backup_dir)
			sys.exit()
		time_str = match_obj.group(1)
		res = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
		return res

	def _get_backup_folder(self):
		""" return latest backup folder """

		backups_root = None
		if sys.platform == "win32":
			backups_root = os.path.expandvars(r"%appdata%\Apple Computer\MobileSync\Backup")
		elif sys.platform == "darwin":
			backups_root = os.path.expanduser("~/Library/Application Support/MobileSync/Backup")
		else:
			print("Unsupported system: %s" % sys.platform)
			return None

		list_of_backups = os.listdir(backups_root)
		list_of_backups = [os.path.join(backups_root, d) for d in list_of_backups]
		list_of_backups = [d for d in list_of_backups if os.path.isdir(d)]

		backup_folders_with_times = [(d, self._backup_time(d)) for d in list_of_backups]
		backup_folders_with_times.sort(reverse=True, key=lambda k: k[1])

		result = backup_folders_with_times[0][0]

		return result

	def __init__(self):
		backup_folder = self._get_backup_folder()
		if backup_folder is None:
			print("Could not find backup folder")
			sys.exit()

		mbdb_file = os.path.join(backup_folder, "Manifest.mbdb")

		files_in_backup = mbdb.process_mbdb_file(mbdb_file)

		# file index: map domain+filename to physical file in backup directory
		self.file_index = {}
		for f in files_in_backup:
			domain = str(f['domain'], "ascii")
			filename = str(f['filename'], "ascii")
			file_path = os.path.join(backup_folder, str(f['fileID']))
			self.file_index[(domain, filename)] = file_path

	def get_file_path(self, domain, filename):
		return self.file_index.get((domain, filename), None)

def main_whatsapp(backup_extractor):
	whatsapp_chat_file = backup_extractor.get_file_path("AppDomain-net.whatsapp.WhatsApp", "Documents/ChatStorage.sqlite")

	if whatsapp_chat_file is None:
		print("Could not find WhatsApp Chat file")
		return

	shutil.copy(whatsapp_chat_file, chat_output.CHAT_STORAGE_FILE)
	chat_output.main(backup_extractor)
	os.remove(chat_output.CHAT_STORAGE_FILE)

def main_sms(backup_extractor):
	sms_db_file = backup_extractor.get_file_path("HomeDomain", "Library/SMS/sms.db")
	addressbook = backup_extractor.get_file_path("HomeDomain", "Library/AddressBook/AddressBook.sqlitedb")

	if sms_db_file is None or addressbook is None:
		print("Could not find SMS files")
		return

	shutil.copy(sms_db_file, sms_output.CHAT_STORAGE_FILE)
	shutil.copy(addressbook, sms_output.CONTACT_FILE)
	sms_output.main(backup_extractor)
	os.remove(sms_output.CHAT_STORAGE_FILE)
	os.remove(sms_output.CONTACT_FILE)

def main():
	backup_extractor = BackupExtractor()
	if len(sys.argv) == 2 and sys.argv[1] == "sms":
		main_sms(backup_extractor)
	else:
		main_whatsapp(backup_extractor)

if __name__ == "__main__":
	main()
