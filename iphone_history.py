from __future__ import print_function
import os
import shutil
import sys
import re
import datetime
import mbdb
import whatsapp
import sms


class BackupExtractor(object):
	""" object representing a single backup directory. used to retrieve the device name and
	date of the backup, and convert file paths from the device filesytem to the actual filesytem """
	def __init__(self, dir):
		self._dir = dir
		self._file_index = None
		self._date = datetime.datetime.fromtimestamp(0)
		self._device_name = ""
		self._parse_info_plist()

	def _parse_info_plist(self):
		info_file = os.path.join(self._dir, "Info.plist")
		if not os.path.exists(info_file):
			print("WARNING: no Info.plist file found in backup folder %s" % (self._dir,))
			return
		info_data = open(info_file, "r").read()
		match_obj = re.search("<date>([^<]*)</date>", info_data)
		if match_obj is not None:
			time_str = match_obj.group(1)
			self._date = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
		else:
			print("WARNING: no date found for backup folder %s" % (self._dir,))
		match_obj = re.search("<key>Device Name</key>\s*<string>([^<]*)</string>", info_data)
		if match_obj is not None:
			self._device_name = match_obj.group(1)
		else:
			print("WARNING: no device name found in backup folder %s" % (self._dir,))

	def get_date(self):
		return self._date

	def get_device_name(self):
		return self._device_name

	def _get_file_index(self):
		if self._file_index is not None:
			return self._file_index

		mbdb_file = os.path.join(self._dir, "Manifest.mbdb")

		files_in_backup = mbdb.process_mbdb_file(mbdb_file)

		# file index: map domain+filename to physical file in backup directory
		self._file_index = dict()
		for f in files_in_backup:
			domain = f['domain'].decode("utf-8", errors="ignore")
			filename = f['filename'].decode("utf-8", errors="ignore")
			file_path = os.path.join(self._dir, str(f['fileID']))
			self._file_index[(domain, filename)] = file_path
		return self._file_index

	def get_file_path(self, domain, filename):
		return self._get_file_index().get((domain, filename), None)


def get_latest_backup():
	backups_root = None
	if sys.platform == "win32":
		backups_root = os.path.expandvars(r"%appdata%\Apple Computer\MobileSync\Backup")
	elif sys.platform == "darwin":
		backups_root = os.path.expanduser("~/Library/Application Support/MobileSync/Backup")
	else:
		print("Unsupported system: %s" % sys.platform)
		return None

	list_of_backups = os.listdir(backups_root)
	if not list_of_backups:
		return None
	list_of_backups = [os.path.join(backups_root, backup) for backup in list_of_backups]
	list_of_backups = [BackupExtractor(backup) for backup in list_of_backups if os.path.isdir(backup)]

	list_of_backups.sort(key=lambda backup: backup.get_date())

	choose = len(sys.argv) == 2 and sys.argv[-1] == "--choose"
	if choose:
		print("Choose backup:")
		for i, backup in enumerate(list_of_backups, 1):
			print("%d. %s %s" % (i, backup.get_device_name(), backup.get_date()))
		index = int(input()) - 1
	else:
		index = -1		# latest backup

	return list_of_backups[index]

def lib_main(backup_extractor, lib):
	files_to_copy = []
	for phone_path, file_path in lib.FILES:
		# phone_path is either a tuple (domain, filename) or a list of such
		# tuples (in which case, only one of the domain/filename should be copied)
		if type(phone_path) == list:
			existing_file_path = [backup_extractor.get_file_path(*one_path) for one_path in phone_path]
			existing_file_path = [path for path in existing_file_path if path is not None]
			existing_file_path = None if len(existing_file_path) == 0 else existing_file_path[0]
		else:
			existing_file_path = backup_extractor.get_file_path(*phone_path)
		if existing_file_path is None:
			print("Could not find file in backup: {}/{}".format(*phone_path))
			return
		files_to_copy.append((existing_file_path, file_path))

	for existing_file_path, file_path in files_to_copy:
		shutil.copy(existing_file_path, file_path)

	lib.main(backup_extractor)

	for existing_file_path, file_path in files_to_copy:
		os.remove(file_path)

def main():
	backup_extractor = get_latest_backup()
	if backup_extractor is None:
		print("Could not find backup folder")
		sys.exit()

	for lib in [whatsapp, sms]:
		lib_main(backup_extractor, lib)

if __name__ == "__main__":
	main()
