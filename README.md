iphone_history
==============

Get the full chat history from Whatsapp and SMS/iMessage.

Usage
-----

* back up your iPhone using iTunes
* run `python iphone_history.py`

This script will look for the backup folder created by iTunes, extract the WhatsApp database,
and create a folder containing the conversation history with each of your contacts.

To output the history of SMS/iMessage, run: `python iphone_history.py sms`
