# TermRSS
A CLI RSS Reader/Notifier in Python with notification support using FeedParser.
Currently supports Linux only. A Windows version is on the works. 
Made in a week as a hobby project. Pull requests are welcome.

- [TermRSS](#termrss)
  - [Usage](#usage)
    - [Add new feeds](#add-new-feeds)
    - [Remove a feed](#remove-a-feed)
    - [View all your feeds](#view-all-your-feeds)
    - [Update your feeds](#update-your-feeds)
    - [Read entries](#read-entries)
    - [Mark all as read](#mark-all-as-read)
    - [Import feeds](#import-feeds)
  - [Background updater](#background-updater)
  - [The feedinfo.json file](#the-feedinfojson-file)
  - [The config.json file](#the-configjson-file)

## Usage

At any time you can check this documentation from your terminal by running `termrss.py help`

### Add new feeds

    termrss.py add -n NAME -u URL [-c CATEGORIES] [-f]
  

 - Name: ID you want for this feed.
 - Url: Url of the RSS feed, or path of local XML file.
 - Categories (optional): List of categories of this feed, separated by comma.
 - -f (optional): By default, the program will not add a feed to your list if it can't detect any entries published. You can bypass this by adding this flag when running the command.
### Remove a feed

    termrss.py remove -n NAME

 - Name: The ID of the feed you want to remove from your list.

### View all your feeds

    termrss.py show [-c CATEGORIES]
View all of the feeds in your list, the last time they were checked for new entries, and their list of categories.
-c (optional): List of categories, separated by comma. If it's present, will return results from feeds tagged as those categories.
### Update your feeds

    termrss.py update [-c CATEGORIES] [-r]
Checks all of your feeds for any new updates since last time you ran this command. If it has been too soon since your last check (configurable on 'config.json') or the server doesn't return any changes since your last check, it will keep in cache the results of the last time there was an update and return the number of unread entries on the saved version. Otherwise, it updates the saved results and returns the number of updates.

-c (optional): List of categories, separated by comma. If it's present, will return results from feeds tagged as those categories.

-r :Refresh flag. Add this to force the program to download results from the server, even if there are no changes from the saved version. Use this if your cache is missing or damaged.
### Read entries

    termrss.py read [-n NAME] [-a] [-c CATEGORIES]
If you run it without a name, will return (via `less`) entries from each one of your feeds (or each one of your feeds which are marked with the indicated categories) with unread entries. If you indicate a name, will return each entry from that feed, marking the newer ones.

 - Name (optional): ID of the feed you want to read. If it's not present, will return the updated entries of all feeds.
 - -a (optional): Add this flag instead of writing a name to read all entries from all your feeds (or all your categorized feeds; see below.).
 - -c (optional): List of categories, separated by comma. If it's present, will return results from feeds tagged as those categories.

### Mark all as read
```
termrss.py clear [-n NAME] [-c CATEGORIES]
```
Marks the selected (or all) feed(s) as just read.
- Name (optional): If present, only this feed will be marked as read.
- -c (optional): List of categories, separated by comma. If present, each feed that is tagged as one of those categories will be marked as read.

### Import feeds

    termrss.py -import -u PATH
If you export your feeds in an XML or OPML file from another feed reader, you can import them here. The importer will preserve name, URL, and categories.

 - -u: Path to the .xml or .opml file.
## Background updater
If you don't wish to keep checking for new entries manually, the program can check your feeds for you and notify you if there are new entries available. 

    termrss.py start
When you run this command, the program creates a file called "rssclient.pid" on its working directory. This file only contains the PID of the background process, so the program can stop it when you run the `stop` command, and will be deleted once the updater is stopped.
Once the updater is running, the program will check for updates,as in the `update` method, after a certain amount of time. You can configure the frequency of updates in the `update_time_minutes` property of the `config.json` file (default 10 minutes).
If the program finds an entry published at a time after the `last_check` property of that feed, it will show a notification and save the latest version of the feed in cache.
## The feedinfo.json file
This file keeps track of the feeds you've suscribed to, their categories, and the last time you read an entry on that feed.
The structure of the file is as follows:

 - **feedName** [string]: The name you've indicated for this feed.

	 - **url** [string]: The url you've indicated for this feed.
	 -  **last_check** [string]: A parsed DateTime object indicating the last time you 	checked this feed for updates. If it hasn't been checked since it was added, the value is "1960-01-01 00:00:00"
	 - **categories** [list of strings]: A list of categories for this feed.
	 - **last_read** [string]: A parsed DateTime object indicated the last time you ran the "read" command on this feed. If it hasn't been checked since it was added, the value is "1960-01-01 00:00:00"
	 - **etag** [string]: The etag property of the feed, if it had one. Used to check changes. The program will update the cache if this property is different to the server's.
	 - **last-modified** [string]: The last time the feed was modified, if it returned it. Used to check changes (see etag)
	 - **unread** [int]: Number of entries saved on cache and published after the last time `read` was run on this feed.
	 - **valid** [bool]: If this is false, the program has detected some problem with the feed and will not update it any longer. You will be asked to remove this feed when you run the `update` command. Feeds are marked as not valid when the server returns a 410 HTTP code, indicating it has been deleted.

## The config.json file
This file allows you to configure certain parameters of the program.
The structure of the file is as follows:

 - **update_time_minutes** *Default 10*: Amount of time the background updater will wait until it checks again for new entries on your feeds.
 - **enable_color_output** *Default True*: If enabled, the program will colorize some of the output strings to make easier to distinguish them. Disable this if you use a custom color scheme in your
 terminal and it's making hard for you to read the text.
 - **verbose_mode** *Default False*: If enabled, will output diverse debugging messages. It shouldn't be enabled unless the program is not working correctly.
