#!/usr/bin/env python

import os
import shutil
import sys
import re
import datetime
import mbdb
import chat_output

class BackupExtractor():
	def _backup_time(self, backup_dir):
		# time of backup is stored in info.plist, which is in xml format
		info_file = os.path.join(backup_dir, "Info.plist")
		info_data = open(info_file, "r").read()
		match_obj = re.search("<date>(.*?)</date>", info_data)
		if match_obj is None:
			return None		# TODO if this happens the script will crash
		time_str = match_obj.group(1)
		res = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
		return res

	def _get_backup_folder(self):
		# return latest backup folder
		# don't be confused between:
		# - backups_folder (root dir of backups)
		# - backup_folders (list of all folders of backups)
		# - backup_folder (result)

		backups_folder = None
		if sys.platform == "win32":
			backups_folder = os.path.expandvars(r"%appdata%\Apple Computer\MobileSync\Backup")
		elif sys.platform == "darwin":
			backups_folder = os.path.expanduser("~/Library/Application Support/MobileSync/Backup")
		else:
			print("Unsupported system: %s" % sys.platform)
			return None

		backup_folders = os.listdir(backups_folder)
		backup_folders = [os.path.join(backups_folder, d) for d in backup_folders]
		backup_folders = [d for d in backup_folders if os.path.isdir(d)]

		backup_folders_with_times = [(d, self._backup_time(d)) for d in backup_folders]
		backup_folders_with_times.sort(reverse=True, key=lambda k: k[1])

		backup_folder = backup_folders_with_times[0][0]

		return backup_folder
	
	def __init__(self):
		backup_folder = self._get_backup_folder()
		if backup_folder is None:
			raise Exception("Could not find backup folder")

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

def main():
	backup_extractor = BackupExtractor()

	whatsapp_chat_file = backup_extractor.get_file_path("AppDomain-net.whatsapp.WhatsApp", "Documents/ChatStorage.sqlite")

	if whatsapp_chat_file is None:
		print("Could not find WhatsApp Chat file")
		sys.exit()

	shutil.copy(whatsapp_chat_file, chat_output.CHAT_STORAGE_FILE)

	chat_output.main()

	os.remove(chat_output.CHAT_STORAGE_FILE)

if __name__ == "__main__":
	main()
