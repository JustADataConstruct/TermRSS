# RSSClient
A RSS Reader/Notifier in Python with notification support using FeedParser
WIP.

- [RSSClient](#rssclient)
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

### Add new feeds

    main.py add -n NAME -u URL [-c CATEGORIES] [-f]
  

 - Name: ID of this feed. Doesn't need to be the "correct" name of the feed.
 - Url: Url of the RSS feed, or path of local XML file.
 - Categories (optional): List of categories of this feed, separated by comma.
 - -f (optional): By default, the program will not add a feed to your list if it can't detect any entries published. You can bypass this by adding this flag when running the command.
### Remove a feed

    main.py remove -n NAME

 - Name: The ID of the feed you want to remove from your list.

### View all your feeds

    main.py show [-c CATEGORIES]
View all of the feeds in your list, the last time they were check for new entries, and their list of categories.
-c (optional): List of categories, separated by comma. If it's present, will return results from feeds tagged as those categories.
### Update your feeds

    main.py update [-c CATEGORIES]
Checks all of your feeds and returns number of entries published after your last check. Does not update the "last_check" property of the feed.
-c (optional): List of categories, separated by comma. If it's present, will return results from feeds tagged as those categories.
### Read entries

    main.py read [-n NAME] [-a] [-c CATEGORIES]
Shows the newer entries on the selected feed since your last check, or every entry on that feed. Will update the "last_check" property of the feed.

 - Name (optional): ID of the feed you want to read. If it's not present, will return the results of all feeds.
 - -a (optional): If this flag is present, will show each entry on the feed instead of the newer entries.
 - -c (optional): List of categories, separated by comma. If it's present, will return results from feeds tagged as those categories.

### Mark all as read
```
main.py clear [-n NAME] [-c CATEGORIES]
```
Marks the selected (or all) feed(s) as just read, without printing the entries.
- Name (optional): If present, only this feed will be marked as read.
- -c (optional): List of categories, separated by comma. If present, each feed that is tagged as one of those categories will be marked as read.

### Import feeds

    main.py -import -u PATH
If you export your feeds in an XML or OPML file from another feed reader, you can import them here. The importer will preserve name, URL, and categories.

 - -u: Path to the .xml or .opml file.
## Background updater
If you don't wish to keep checking for new entries manually, the program can check your feeds for you and notify you if there are new entries available. 

    main.py start
When you run this command, the program creates a file called "rssclient.pid" on its working directory. This file only contains the PID of the background process, so the program can stop it when you run the `stop` command, and will be deleted once the updater is stopped.
Once the updater is running, the program will check for updates,as in the `update` method, after a certain amount of time. You can configure the frequency of updates in the `update_time_minutes` property of the `config.json` file (default 1 minute).
If the program finds an entry published at a time after the `last_check` property of that feed, it will show a notification. Please note that this doesn't mark that feed as read: you will be notificated of the same entry each time the program runs until you run `read` or stop the updater.
## The feedinfo.json file
This file keeps track of the feeds you've suscribed to, their categories, and the last time you read an entry on that feed.
The structure of the file is as follows:

 - **feedName** [string]: The name you've indicated for this feed.

	 - **url** [string]: The url you've indicated for this feed.
	 -  **last_check** [string]: A parsed DateTime object indicating the last time you 	checked this feed. If it hasn't been checked since it was added, the value is "1960-01-01 00:00:00"
	 - **categories** [list of strings]: A list of categories for this feed.

## The config.json file
This file allows you to configure certain parameters of the program.
The structure of the file is as follows:

 - **update_time_minutes** *Default 10*: Amount of time the background updater will wait until it checks again for new entries on your feeds.
 - **enable_color_output** *Default True*: If enabled, the program will colorize some of the output strings to make easier to distinguish them. Disable this if you use a custom color scheme in your
 terminal and it's making hard for you to read the text.
