import feedparser
import json
import argparse

#TODO:
# Update and show new entries since last time
# Some kind of GUI (?)
#   View items on the program, open them in browser, scroll support...
# Notification support

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
        #print(feeds)
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

def show_feeds():
    for n in feeds:
        print(f"{n} : {feeds[n]}")

parser = argparse.ArgumentParser()
parser.add_argument("-c","--command",help="Add a feed, remove a feed or show all feeds",choices=['add','remove','show'])
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
    else:
        parser.print_help()
else:
    parser.print_help()