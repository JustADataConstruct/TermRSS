import feedparser
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
# Move the lastcheck to the json file, so each feed can have its own update date. Allows us to get data from
#   new feeds without having to use -all
# Opml import support

feeds = {}

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
    feeds["Feeds For All Sample Feed"] = 'https://www.feedforall.com/sample.xml'
    save_feed_file()


def add_feed(feedname,feedURL):
    feeds[feedname] = feedURL
    save_feed_file()

def remove_feed(feedname):
    if feeds[feedname] !=None:
        feeds.pop(feedname)
        save_feed_file()

def view_updates(name,showall,to_console=True):
    try:
        with open('lastcheck.txt') as f:
            lastcheck = datetime.strptime(f.read(),'%Y-%m-%d %H:%M:%S')
            f.close()
    except IOError as e:
        w = open('lastcheck.txt','w')
        w.write(str(datetime(1960,1,1,0,0,0)))
        w.close()
        lastcheck = datetime(1960,1,1,0,0,0)
    if name != None and feeds[name] != None:
        s = feedparser.parse(feeds[name])
        if to_console:
            print(f"----[{name.upper()} - {feeds[name]}]----")
        print_entries(s,lastcheck,showall,to_console)
    else:
        for n in feeds:
            s = feedparser.parse(feeds[n])
            if to_console:
             print(f"----[{n.upper()} - {feeds[n]}]----")
            print_entries(s,lastcheck,showall,to_console)
    
    if to_console: #FIXME: With this, the same notifications would repeat each time until the user does a manual update. Do we really like this?
        w = open("lastcheck.txt","w")
        w.write(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        w.close()

def print_entries(feed,lastcheck,showall,to_console):
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
        else: #Don't spam notifications if we're doing a manual check.
            sp.call(['notify-send',e.title,e.link]) #FIXME: Should we use other method instead of notify-send?
        
def show_feeds():
    for n in feeds:
        print(f"{n} : {feeds[n]}")

parser = argparse.ArgumentParser()
parser.add_argument("command",help="Add:Add a new feed\nRemove:Remove a feed\nShow:View list of feeds\nUpdate:View latest updates",choices=['update','add','remove','show','start','stop'])
parser.add_argument("-n","--name",help="Name of the feed you want to add/remove")
parser.add_argument("-u","--url",help="Url of the feed you want to add.")

#Flags
parser.add_argument("-a","--all",help="When calling update, show all elements in a feed, even those already in the past.",action='store_true')
parser.add_argument("--bg",help="System flag to start the background updater. Do not use.",action="store_true")

args = parser.parse_args()

if args.bg:
    schedule.every(10).seconds.do(view_updates,name=None,showall=False,to_console=False)
    while True:
        schedule.run_pending()
        time.sleep(1)    

if args.command != None:
    if args.command.lower() == "add":
        if args.name == None or args.url == None:
            parser.print_help()
        else:
            add_feed(args.name,args.url)
            print("Feed added!")
    elif args.command.lower() == "remove":
        if args.name == None:
            parser.print_help()
        else:
            remove_feed(args.name)
            print("Feed removed!")
    elif args.command.lower() == "show":
        show_feeds()
    elif args.command.lower() == "update":
        view_updates(args.name,args.all)
    elif args.command.lower() == "start": #FIXME: Prevent this for running twice; check if the file exists.
        if os.path.isfile("rssclient.pid"):
            print("Background updater already running!")
        else:
            view_updates(None,False,True)
            proc = sp.Popen(["python","main.py","show","--bg"])
            w = open("rssclient.pid","w")
            w.write(str(proc.pid))
            w.close()
            print("Background updater started successfully.")
    elif args.command.lower() == "stop":
        with open('rssclient.pid') as f:
            pid = f.read()
            os.kill(int(pid),9)
            f.close()
        os.remove('rssclient.pid')
        print("Background updater stopped successfully.")
    else:
        parser.print_help()
else:
    parser.print_help()
