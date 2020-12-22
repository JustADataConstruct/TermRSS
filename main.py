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
# Notification support (WIP) Some action when the notification shows up.
# An HTML export to see entries in a prettier way?
# Autodetect feed from url.
# Windows support? Pack into exe?
# Set update frequency for each feed?

feeds = {}
config = {}

def save_feed_file():
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
    feeds["SAMPLE FEED"] = {
        'url':'https://www.feedforall.com/sample.xml',
        'last_check': str(datetime(1960,1,1,0,0,0)),
        'categories':[]
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

def add_feed(feedname,feedURL,categories=[],force=False):
    try:
        f = feedparser.parse(feedURL)
    except Exception as e:
        print(f"Something went wrong when trying to parse this feed: {e}")
        return
    if len(f.entries) == 0 and force == False :
        print("No entries detected. Please make sure this URL is a valid feed. If you are sure the URL is correct, repeat the add command with the '-f' flag to forceadd it.")
        return
    feeds[feedname.upper()] = {
        'url':feedURL,
        'last_check':str(datetime(1960,1,1,0,0,0)),
        'categories':categories
    }
    save_feed_file()
    print("Feed added!")

def remove_feed(feedname):
    if feeds[feedname.upper()] !=None:
        feeds.pop(feedname.upper())
        save_feed_file()

def check_new_entries(to_console=True,categories=[]): #FIXME: If the updater is running and we add a new feed, it isn't included on the autoupdates. We need to reload the file.
    entrynumber = {}
    if to_console:
        print("Checking for new entries...")
    if len(categories) > 0:
        lst = [x for x in feeds if any(item in categories for item in feeds[x]["categories"])]
    else:
        lst = feeds
    for n in lst:
        i = 0
        last_check = datetime.strptime(feeds[n]["last_check"],'%Y-%m-%d %H:%M:%S')
        s = feedparser.parse(feeds[n]["url"])
        for e in s.entries:
            p_date = datetime.fromtimestamp(time.mktime(e.published_parsed))
            if p_date > last_check: #If newer.
                i = i+1
        entrynumber[n]=i
    for k in entrynumber:
        n = entrynumber[k]
        if to_console:
            print(f"{k}: {n} update(s)")
        else:
            if n > 0:
                sp.call(['notify-send',k,f"{n} updates(s)"]) #FIXME: Should we use other method instead of notify-send?


def read_updates(name,showall,categories=[]): 
    if name != None and feeds[name.upper()] != None:
        lastcheck = datetime.strptime(feeds[name.upper()]["last_check"],'%Y-%m-%d %H:%M:%S')
        s = feedparser.parse(feeds[name.upper()]["url"])
        url = feeds[name.upper()]["url"]
        print(f"----[{name.upper()} - {url}]----")
        print_entries(s,lastcheck,showall)
        feeds[name.upper()]["last_check"]= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        if len(categories) > 0:
            lst = [x for x in feeds if any(item in categories for item in feeds[x]["categories"])]
        else:
            lst = feeds
        for n in lst:
            lastcheck = datetime.strptime(feeds[n]["last_check"],'%Y-%m-%d %H:%M:%S')
            s = feedparser.parse(feeds[n]["url"])
            url = feeds[n]["url"]
            print(f"----[{n.upper()} - {url}]----")
            print_entries(s,lastcheck,showall)
            feeds[n]["last_check"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')    
    save_feed_file()
        
def print_entries(feed,lastcheck,showall):
    for e in feed.entries:
        p_date = datetime.fromtimestamp(time.mktime(e.published_parsed))
        if showall == False and p_date < lastcheck:
            break
        descriptionsoup = BeautifulSoup(e.description,'html.parser')
        print(e.title)
        print(e.link)
        print(descriptionsoup.get_text())
        print(e.published)
        print('\n')       
        
def show_feeds(categories = []):
    if len(categories) > 0:
        f = [x for x in feeds if any(item in categories for item in feeds[x]["categories"])]
        for k in f:
            print(f"{k} : {feeds[k]}")
    else:
        for n in feeds:
            print(f"{n} : {feeds[n]}")

def import_feeds(source):
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
parser.add_argument("command",help="Add:Add a new feed\nRemove:Remove a feed\nShow:View list of feeds\nUpdate:View latest updates",choices=['update','read','add','remove','show','start','stop','import']) #FIXME: Update help
parser.add_argument("-n","--name",help="Name of the feed you want to add/remove")
parser.add_argument("-u","--url",help="Url of the feed you want to add.")

#Flags
parser.add_argument("-a","--all",help="When calling update, show all elements in a feed, even those already in the past.",action='store_true')
parser.add_argument("--bg",help="System flag to start the background updater. Do not use.",action="store_true")
parser.add_argument("-c","--categories",help="When adding a feed, list of categories, separated by comma.")
parser.add_argument("-f","--force-add",help="Force add a feedd to your list, even if it has no entries.",action="store_true")

args = parser.parse_args()

if args.bg:
    schedule.every(config["update_time_minutes"]).minutes.do(check_new_entries,to_console=False)
    while True:
        schedule.run_pending()
        time.sleep(1)    

if args.categories != None:
    categories = list(args.categories.split(','))
else:
    categories = []

if args.command != None:
    if args.command.lower() == "add":
        if args.name == None or args.url == None:
            parser.print_help()
        else:
            add_feed(args.name,args.url,categories,args.force_add)
    elif args.command.lower() == "remove":
        if args.name == None:
            parser.print_help()
        else:
            remove_feed(args.name)
            print("Feed removed!")
    elif args.command.lower() == "show":
        show_feeds(categories)
    elif args.command.lower() == "update":
        check_new_entries(True,categories)
    elif args.command.lower() == "read":
        read_updates(args.name,args.all,categories)
    elif args.command.lower() == "start":
        if os.path.isfile("rssclient.pid"):
            print("Background updater already running!")
        else:
            try:
                proc = sp.Popen(["python","main.py","show","--bg"])
                w = open("rssclient.pid","w")
                w.write(str(proc.pid))
                w.close()
                time = config["update_time_minutes"]
                print(f"Background updater started successfully. Will check for new entries every {time} minutes")
            except Exception as e:
                print(f"Something went wrong when trying to run the updater: {e}")
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
