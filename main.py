import feedparser
import json
import argparse
from bs4 import BeautifulSoup

#TODO:
# Update and show new entries since last time - https://stackoverflow.com/questions/474528/what-is-the-best-way-to-repeatedly-execute-a-function-every-x-seconds
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

def view_updates(name): #TODO: Only show updates since last time checked.
    if name != None and feeds[name] != None:
        s = feedparser.parse(feeds[name])
        print(f"----[{name.upper()} - {feeds[name]}]----")
        for i in range(0,9):
            descriptionsoup = BeautifulSoup(s.entries[i].description,'html.parser')
            print(s.entries[i].title)
            print(s.entries[i].link)
            print(descriptionsoup.get_text())
            print(s.entries[i].published)
            print('\n')
    else:
        for n in feeds:
            s = feedparser.parse(feeds[n])
            print(f"----[{n.upper()} - {feeds[n]}]----")
            for i in range(0,9):
                descriptionsoup = BeautifulSoup(s.entries[i].description,'html.parser')
                print(s.entries[i].title)
                print(s.entries[i].link)
                print(descriptionsoup.get_text())
                print(s.entries[i].published)
                print('\n')
                
def show_feeds():
    for n in feeds:
        print(f"{n} : {feeds[n]}")

parser = argparse.ArgumentParser()
parser.add_argument("-c","--command",help="Add:Add a new feed\nRemove:Remove a feed\nShow:View list of feeds\nUpdate:View latest updates",choices=['update','add','remove','show'])
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