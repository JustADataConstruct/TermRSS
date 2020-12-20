import feedparser
import json
import argparse
from bs4 import BeautifulSoup
from datetime import datetime
from time import mktime

#TODO:
# Update and show new entries since last time - https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds
# Some kind of GUI (?)
#   View items on the program, open them in browser, scroll support...
# Notification support
# Work in the background as a daemon, updating and showing notifications. Or just leave it minimized?

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

def view_updates(name): #TODO: Show all even if already in the past.
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
        print(f"----[{name.upper()} - {feeds[name]}]----")
    else:
        for n in feeds:
            s = feedparser.parse(feeds[n])
            print(f"----[{n.upper()} - {feeds[n]}]----")
    for e in s.entries:
        p_date = datetime.fromtimestamp(mktime(e.published_parsed))

        if p_date < lastcheck:
            break
        descriptionsoup = BeautifulSoup(e.description,'html.parser')
        print(e.title)
        print(e.link)
        print(descriptionsoup.get_text())
        print(e.published)
        print('\n')
    w = open("lastcheck.txt","w")
    w.write(str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    w.close()

def show_feeds():
    for n in feeds:
        print(f"{n} : {feeds[n]}")

parser = argparse.ArgumentParser()
parser.add_argument("command",help="Add:Add a new feed\nRemove:Remove a feed\nShow:View list of feeds\nUpdate:View latest updates",choices=['update','add','remove','show'])
parser.add_argument("-n","--name",help="Name of the feed you want to add/remove")
parser.add_argument("-u","--url",help="Url of the feed you want to add.")

args = parser.parse_args()

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
        view_updates(args.name)
    else:
        parser.print_help()
else:
    parser.print_help()