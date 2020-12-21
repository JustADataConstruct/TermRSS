import feedparser
import listparser
import json
import argparse
from bs4 import BeautifulSoup
from datetime import datetime
import subprocess as sp
import time
import schedule
import os


#TODO:
# Some kind of GUI (?)
#   View items on the program, open them in browser, scroll support...
#   Is this really needed?
# Notification support (WIP)
# An HTML export to see entries in a prettier way?
# Autodetect feed from url.
# Windows support? Pack into exe?
# Some kind of validation, making sure feeds work before adding them.
# Better error handling and what to do when feeds fail (and why do they fail)
# Change how we update: when we call update, we only print the title of each entry. Add a function read (main.py read -n FEED) to actually read the updates and mark the feed as checked.

feeds = {}
config = {}

def save_feed_file():
    """Writes the content of the feeds dictionary into a json file.
    """
    f = open('feedinfo.json','w')
    s = json.dumps(feeds)
    f.write(s)
    f.close()

try:
    with open('feedinfo.json') as f:
        s = f.read()
        feeds = json.loads(s)
        f.close()
except IOError as e:
    print("Feedinfo not found! Recreating it now.")
    feeds["Feeds For All Sample Feed"] = {
        'url':'https://www.feedforall.com/sample.xml',
        'last_check': str(datetime(1960,1,1,0,0,0)),
        'categories:':[]
    }
    save_feed_file()

try :
    with open('config.json') as f:
        s = f.read()
        config = json.loads(s)
        f.close()
except IOError as e:
    print("Config file not found. Going back to defaults.")
    config["update_time_minutes"] = 1

def add_feed(feedname,feedURL,categories= []):
    """Adds a new entry to the feeds dictionary, using feedname as key and feedURL as value, then saves the dictionary into a json file

    Args:
        feedname (string): Identifier for this feed. Doesn't have to be the feed actual name.
        feedURL (string): Direct URL for the RSS feed.
        categories (string[], optional): List of categories for this feed, if any, separated by comma.
    """
    feeds[feedname.upper()] = {
        'url':feedURL,
        'last_check':str(datetime(1960,1,1,0,0,0)),
        'categories':categories
    }
    save_feed_file()

def remove_feed(feedname):
    """Pops the indicated feed from the feeds dictionary and commits changes to the json file.

    Args:
        feedname (string): Name of the feed to remove
    """
    if feeds[feedname.upper()] !=None:
        feeds.pop(feedname.upper())
        save_feed_file()

def view_updates(name,showall,to_console=True): #FIXME: If the updater is running and we add a new feed, it isn't included on the autoupdates. We need to reload the file.
    """Get latest updates from the feeds. By default gets the entries published after the last check time
       and prints them to the console.

    Args:
        name (string): If this is the name of an existing feed, only entries of that feed will be returned. If None, grabs entries from all feeds on file.
        showall (bool): If True, prints every entry in the feed instead of just the newer ones.
        to_console (bool, optional): If true, prints results to the console. Defaults to True.
    """
    if name != None and feeds[name.upper()] != None:
        lastcheck = datetime.strptime(feeds[name.upper()]["last_check"],'%Y-%m-%d %H:%M:%S')
        s = feedparser.parse(feeds[name.upper()]["url"])
        if to_console:
            url = feeds[name.upper()]["url"]
            print(f"----[{name.upper()} - {url}]----")
        print_entries(s,lastcheck,showall,to_console)
        feeds[name.upper()]["last_check"]= datetime.now().strftime('%Y-%m-%d %H:%M:%S') #TODO: This marks them as read once the notification shows up. Do we like that?
    else:
        for n in feeds:
            lastcheck = datetime.strptime(feeds[n]["last_check"],'%Y-%m-%d %H:%M:%S')
            s = feedparser.parse(feeds[n]["url"])
            if to_console: 
                url = feeds[n]["url"]
                print(f"----[{n.upper()} - {url}]----")
            print_entries(s,lastcheck,showall,to_console)
            feeds[n]["last_check"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')    
    save_feed_file()
        
def print_entries(feed,lastcheck,showall,to_console):
    """Either prints entries in a feed into the console or shows a notification from each entry. This function is called by
    view_updates and shouldn't be called manually.

    Args:
        feed (string): Name of the feed.
        lastcheck (datetime): Datetime object of the last time the feeds were checked.
        showall (bool): If True, prints every entry in the feed instead of just the newer ones.
        to_console ([bool]): If true, prints results to the console
    """
    for e in feed.entries:
        p_date = datetime.fromtimestamp(time.mktime(e.published_parsed))

        if showall == False and p_date < lastcheck:
            break
        descriptionsoup = BeautifulSoup(e.description,'html.parser')
        if to_console:
            print(e.title)
            print(e.link)
            print(descriptionsoup.get_text())
            print(e.published)
            print('\n')
        else:
            sp.call(['notify-send',e.title,e.link]) #FIXME: Should we use other method instead of notify-send?
        
        
def show_feeds():
    """Returns a list of each feed in file.
    """
    for n in feeds:
        print(f"{n} : {feeds[n]}")

def import_feeds(source):
    """Grabs a opml file and tries to parse and import.

    Args:
        source (string): Either an URL or a local path to the opml file.
    """
    result = listparser.parse(source)
    name = result.meta.title
    size = len(result.feeds)
    print(f"Do you want to import {size} feeds from {name}? [y]es/[n]o/[v]iew")
    answer = input()
    if answer.lower() == "v" or answer.lower() == "view":
        for i in result.feeds:
            print(f"{i.title} : {i.url}")
    elif answer.lower() == "y" or answer.lower() == "yes":
        try:
            for i in result.feeds:
                if len(i.categories) > 0:
                    categories = i.categories[0]
                else:
                    categories = []
                add_feed(i.title,i.url,categories)
        except Exception as e:
            print(f"Something went wrong when importing feeds!: {e}")
            return
        print("Feeds imported successfully.")
        

parser = argparse.ArgumentParser()
parser.add_argument("command",help="Add:Add a new feed\nRemove:Remove a feed\nShow:View list of feeds\nUpdate:View latest updates",choices=['update','add','remove','show','start','stop','import']) #FIXME: Update help
parser.add_argument("-n","--name",help="Name of the feed you want to add/remove")
parser.add_argument("-u","--url",help="Url of the feed you want to add.")

#Flags
parser.add_argument("-a","--all",help="When calling update, show all elements in a feed, even those already in the past.",action='store_true')
parser.add_argument("--bg",help="System flag to start the background updater. Do not use.",action="store_true")
parser.add_argument("-c","--categories",help="When adding a feed, list of categories, separated by comma.")

args = parser.parse_args()

if args.bg:
    schedule.every(config["update_time_minutes"]).minutes.do(view_updates,name=None,showall=False,to_console=False)
    while True:
        schedule.run_pending()
        time.sleep(1)    

if args.command != None:
    if args.command.lower() == "add":
        if args.name == None or args.url == None:
            parser.print_help()
        else:
            if args.categories != None:
                categories = list(args.categories.split(','))
            else:
                categories = []
            add_feed(args.name,args.url,categories)
            print("Feed added!")
    elif args.command.lower() == "remove":
        if args.name == None:
            parser.print_help()
        else:
            remove_feed(args.name)
            print("Feed removed!")
    elif args.command.lower() == "show": #TODO: Filter for categories.
        show_feeds()
    elif args.command.lower() == "update":
        view_updates(args.name,args.all)
    elif args.command.lower() == "start":
        if os.path.isfile("rssclient.pid"):
            print("Background updater already running!")
        else:
            view_updates(None,False,True)
            proc = sp.Popen(["python","main.py","show","--bg"])
            w = open("rssclient.pid","w")
            w.write(str(proc.pid))
            w.close()
            time = config["update_time_minutes"]
            print(f"Background updater started successfully. Will check for new entries every {time} minutes")
    elif args.command.lower() == "stop":
        try:
            with open('rssclient.pid') as f:
                pid = f.read()
                os.kill(int(pid),9)
                f.close()
            os.remove('rssclient.pid')
            print("Background updater stopped successfully.")            
        except IOError as e:
            print("Background updater is not running.")
    elif args.command.lower() == "import":
        if args.url == None:
            print("Usage: main.py import -u [OPML URL OR LOCAL PATH]")
        else:
            import_feeds(args.url)
    else:
        parser.print_help()
else:
    parser.print_help()
