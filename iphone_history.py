from __future__ import print_function
import os
import shutil
import sys
import re
import datetime
import mbdb
import whatsapp
import sms

class BackupExtractor():
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
			domain = f['domain'].decode("ascii")
			filename = f['filename'].decode("ascii")
			file_path = os.path.join(backup_folder, str(f['fileID']))
			self.file_index[(domain, filename)] = file_path

	def _backup_time(self, backup_dir):
		# time of backup is stored in info.plist, which is in xml format
		info_file = os.path.join(backup_dir, "Info.plist")
		info_data = open(info_file, "r").read()
		match_obj = re.search("<date>(.*?)</date>", info_data)
		if match_obj is None:
			print("WARNING: Could not find date of backup from %s. Assigning oldest date" % backup_dir)
			return datetime.datetime.fromtimestamp(0)
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
		if not list_of_backups:
			return None
		list_of_backups = [os.path.join(backups_root, d) for d in list_of_backups]
		list_of_backups = [d for d in list_of_backups if os.path.isdir(d)]

		backup_folders_with_times = [(d, self._backup_time(d)) for d in list_of_backups]
		backup_folders_with_times.sort(reverse=True, key=lambda k: k[1])

		result = backup_folders_with_times[0][0]

		return result

	def get_file_path(self, domain, filename):
		return self.file_index.get((domain, filename), None)

def lib_main(backup_extractor, lib):
	files_to_copy = []
	for domain, filename, new_file_path in lib.FILES:
		existing_file_path = backup_extractor.get_file_path(domain, filename)
		if existing_file_path is None:
			print("Could not find file in backup: {}/{}".format(domain, filename))
			return
		files_to_copy.append((existing_file_path, new_file_path))

	for existing_file_path, new_file_path in files_to_copy:
		shutil.copy(existing_file_path, new_file_path)

	lib.main(backup_extractor)

	for existing_file_path, new_file_path in files_to_copy:
		os.remove(new_file_path)

def main():
	backup_extractor = BackupExtractor()

	for lib in [whatsapp, sms]:
		lib_main(backup_extractor, lib)

if __name__ == "__main__":
	main()
