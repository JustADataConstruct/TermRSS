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
import tempfile

from output_helper import OutputHelper
from cache_helper import CacheHelper

feeds = {}
config = {}

try :
    with open('config.json') as f:
        s = f.read()
        config = json.loads(s)
except IOError as e:
    print("Config file not found. Going back to defaults.")
    config["update_time_minutes"] = 10
    config["enable_color_output"] = True
    config["verbose_mode"] = False

output = OutputHelper(config["enable_color_output"])
cache = CacheHelper(output,config)

verbose = config["verbose_mode"]

def save_feed_file():
    """Saves changes made to the feeds dictionary to the feedinfo.json file.
    """
    if verbose:print("Trying to save file...")
    f = open('feedinfo.json','w')
    s = json.dumps(feeds,indent=4)
    f.write(s)
    if verbose:print("Saved.")
    f.close()

def add_feed(feedname,feedURL,categories=[],force=False):
    """Adds a new feed to the feeds dictionary and saves it to file. Handles errors and
    restarting the updater.

    Args:
        feedname (string): Name to identify the feed.
        feedURL (string): The URL of the feed.
        categories (list of strings, optional): A string of categories separated by comma. Defaults to [].
        force (bool, optional): If True, will add the feed even if entries can't be detected. Defaults to False.
    """
    if feedURL.startswith(('http://','https://')) == False:
        if verbose:print("Checking if url has prefix...")        
        feedURL = "http://" + feedURL
    try:
        if verbose:print("Trying to parse feed...")
        f = feedparser.parse(feedURL)
    except Exception as e:
        output.write_error(f"Something went wrong when trying to parse this feed ({feedname}): {e}")
        return
    if len(f.entries) == 0 and force == False :
        output.write_error(f"No entries detected on feed {feedname}. Please make sure this URL is a valid feed. If you are sure the URL is correct, repeat the add command with the '-f' flag to forceadd it.")
        return
    etag = f.etag if hasattr(f,'etag') else ""
    modified = f.modified if hasattr(f,'modified') else ""
    initdate = str(datetime(1960,1,1,0,0,0))
    feeds[feedname.upper()] = {
        'url':feedURL,
        'last_check':initdate,
        'last_read':initdate,
        'categories':categories,
        'etag':etag,
        'last-modified':modified,
        'unread':len(f.entries),
        'valid':True
    }
    if f.bozo == 1:
        output.write_error(f"A problem was detected with your feed:{f.bozo_exception}. You may find problems when reading its entries. Do you want to add it? [Y]es/[N]o")
        answer = input()
        if answer.lower() == "n" or answer.lower() == "no":
            return
        
    save_feed_file()
    cache.save_cache_file(feedname,f)
    output.write_ok(f"Feed {feedname} added!") 
    if is_updater_running():
        #This is needed so the background process can reload the feed list. It's not pretty but it works.
        stop_background_updater(True)
        start_background_updater(True)

def remove_feed(feedname):
    """Removes a feed from the feeds dictionary, removes that feed from the cache file, and
    saves the changes to disl.

    Args:
        feedname (string): Name of the feed to remove.
    """
    if feeds[feedname.upper()] !=None:
        if verbose:print("Feed exists, removing.")
        feeds.pop(feedname.upper())
        save_feed_file()
        cache.remove_from_cache(feedname)

def check_new_entries(to_console=True,categories=[],force_refresh=False):
    """Tries to fetch new entries from the server. Calls check_cache_valid to handle the actual
    fetching and getting the latest version.

    Args:
        to_console (bool, optional): If true, will output to terminal. False when using the
        background process.. Defaults to True.
        categories (ist of strings, optional): String with a list of categories, separated by comma.. Defaults to [].
        force_refresh (bool, optional): If true, will tell check_cache_valid to download
        from the server even if there are no changes.. Defaults to False.
    """
    if to_console:
        output.write_info("Checking for new entries...")
    if len(categories) > 0:
        lst = [x for x in feeds if any(item in categories for item in feeds[x]["categories"])]
        if verbose:print("Filtering categories...")
    else:
        lst = feeds
        if verbose:print("Using main feed list.")
    for n in lst:
        if feeds[n]["valid"] == False:
            if to_console:
                output.write_error(f"{n} is no longer valid and will not be updated. Please remove it from your list.")
            else:
                sp.call(['notify-send',n,f"Invalid feed."])
            continue
        last_check = datetime.strptime(feeds[n]["last_check"],'%Y-%m-%d %H:%M:%S')
        cache.check_cache_valid(n,feeds[n],last_check,to_console,force_refresh)
        feeds[n]["last_check"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_feed_file()

def read_updates(name,all = False,categories=[]): 
    """Grabs entries from cache and outputs them via the less command.

    Args:
        name (string): Name of the feed that wants to be read. If none, grabs all updated unless
        categories is not empty.
        all (bool, optional): If True, shows all feeds (categorized or existing). Defaults to False.
        categories (list of strings, optional): String with a list of categories separated
        by comma. Defaults to [].
    """
    text = ""
    if name != None and feeds[name.upper()] != None:
        if verbose:print("Trying to load from cache...")
        s = cache.load_from_cache(name)
        if s == None: return
        text = grab_entries(name,s)
    else:
        if len(categories) > 0:
            lst = [x for x in feeds if any(item in categories for item in feeds[x]["categories"])]
            if verbose:print("Filtering categories...")
        else:
            lst = feeds
            if verbose:print("Using main feed list...")
        if all == False:
            lst = [x for x in lst if feeds[x]["unread"] > 0]
            if len(lst) == 0:
                text = "No new entries on any feed. Run read -a to see all past entries."
        for n in lst:
            s = cache.load_from_cache(n)
            if s == None: return
            text += grab_entries(n,s)
    text += "\n['Q' to exit]"
    with tempfile.TemporaryDirectory() as tmp:
        if verbose:print("Calling less")
        path = os.path.join(tmp,"rssentries")
        with open(path,"w") as o:
            o.write(text)
        sp.call(['less','-R',path])
    save_feed_file()

def grab_entries(name,feed):
    """Returns a string with the feed's entries in a nice format.

    Args:
        name (string): Name of the feed.
        feed (dictionary): Actual feed object

    Returns:
        string: All entries requested.
    """
    lastread = datetime.strptime(feeds[name.upper()]["last_read"],'%Y-%m-%d %H:%M:%S') 
    url = feeds[name.upper()]["url"]
    s = output.write_feed_header(f"----[{name.upper()} - {url}]----") + "\n"    

    if verbose:print("Grabbing entries...")
    for e in feed["entries"]:
        p_date = datetime.fromtimestamp(time.mktime(time.struct_time(e["published_parsed"])))  
        desc = BeautifulSoup(e["summary"],'html.parser')
        new = True if p_date > lastread else False
        s += output.format_entry(name,e,desc.get_text(),new)
    feed["last_read"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')    
    feed["unread"] = 0
    return s              

def show_feeds(categories = []):
    """Outputs information from saved feeds.

    Args:
        categories (list of strings, optional): List of categories, separated by
        comma. If present, filters the result. Defaults to [].
    """
    if len(categories) > 0:
        lst= [x for x in feeds if any(item in categories for item in feeds[x]["categories"])]
    else:
        lst = feeds
    for n in lst:
        url = feeds[n]["url"]
        last_checked = feeds[n]["last_check"]
        last_read = feeds[n]["last_read"]
        unread = feeds[n]["unread"]
        valid = feeds[n]["valid"]
        categories = feeds[n]["categories"]
        output.write_info(f"{n}: {url}")
        print(f"Last checked: {last_checked}. Last read: {last_read}")
        print(f"Unread entries: {unread}")
        print(f"Categories: {categories}")
        if valid== False:
            output.write_error("WARNING: This feed is no longer valid and will not be updated.")
        print("\n")

def import_feeds(source):
    """Tries to parse and import an opml file exported from another RSS reader. Will try
    to keep name and categories.

    Args:
        source (string): Path of the opml file.
    """
    result = listparser.parse(source)
    name = result.meta.title
    size = len(result.feeds)
    output.write_info(f"Do you want to import {size} feeds from {name}? [y]es/[n]o/[v]iew")
    answer = input()
    if answer.lower() == "v" or answer.lower() == "view":
        for i in result.feeds:
            print(f"{i.title} : {i.url}")
    elif answer.lower() == "y" or answer.lower() == "yes":
        try:
            for i in result.feeds:
                if verbose:print(f"Trying to add {i.title}")
                if len(i.categories) > 0:
                    if verbose:print("Grabbing categories")
                    categories = i.categories[0]
                else:
                    categories = []
                add_feed(i.title,i.url,categories)
        except Exception as e:
            output.write_error(f"Something went wrong when importing {i}!: {e}")
        finally:
            output.write_ok("Feeds imported successfully.")

def mark_as_read(name,categories=[]):
    """Will update the last_read and unread properties of each feed to set them up to date and
    restart the background updater.

    Args:
        name (string): Name of the feed that wants to be cleared. If none, will apply to all feeds.
        categories (list of strings, optional): If present, will filter results.. Defaults to [].
    """
    if name != None and feeds[name.upper()] != None:
        feed = feeds[name.upper()]
        feed["last_read"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        feed["unread"] = 0
    else:
        if len(categories) > 0:
            lst = [x for x in feeds if any(item in categories for item in feeds[x]["categories"])]
        else:
            lst = feeds
        for f in lst:
            feed = feeds[f]
            feed["last_read"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            feed["unread"] = 0
    save_feed_file()
    if is_updater_running():
        stop_background_updater()
        start_background_updater()


def start_background_updater(silent=False):
    """Will create the rssclient.pid file and start the background process. Time is configurable on the
    config.json file.

    Args:
        silent (bool, optional): [If True, will not print to terminal the status messages]. Defaults to False.
    """
    if verbose:print("Trying to start updater...")
    proc = sp.Popen(["python","main.py","show","--bg"])
    w = open("rssclient.pid","w")
    w.write(str(proc.pid))
    w.close()
    time = config["update_time_minutes"]
    if silent == False:
        if verbose:print("Done")
        output.write_ok(f"Background updater started successfully. Will check for new entries every {time} minute(s)")

def stop_background_updater(silent=False):
    """Will try to remove the rssclient.pid file and stop the background process.

    Args:
        silent (bool, optional): If True, will not print to terminal the status messages.. Defaults to False.
    """
    with open('rssclient.pid') as f:
        pid = f.read()
        os.kill(int(pid),9)
    os.remove('rssclient.pid')
    if silent == False:
        output.write_ok("Background updater stopped successfully.")
def is_updater_running():
    return os.path.isfile("rssclient.pid")


try:
    with open('feedinfo.json') as f:
        s = f.read()
        feeds = json.loads(s)
except IOError as e:
    output.write_error("Feedinfo not found! Recreating it now.")
    initdate = str(datetime(1960,1,1,0,0,0))
    add_feed("Sample feed","https://www.feedforall.com/sample.xml","Test")


parser = argparse.ArgumentParser(add_help=False,usage="Run main.py help to read the manual.")


parser.add_argument("command",choices=['help','update','read','add','remove','show','start','stop','import','clear'])
parser.add_argument("-n","--name")
parser.add_argument("-u","--url")

#Flags
parser.add_argument("-r","--refresh",action='store_true')
parser.add_argument("--bg",action="store_true")
parser.add_argument("-c","--categories")
parser.add_argument("-f","--force-add",action="store_true")
parser.add_argument("-a","--all",action="store_true")

args = parser.parse_args()

if args.bg:
    schedule.every(config["update_time_minutes"]).minutes.do(check_new_entries,to_console=False,force_refresh=False)
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
            output.write_ok("Feed removed!")
    elif args.command.lower() == "show":
        show_feeds(categories)
    elif args.command.lower() == "update":
        check_new_entries(True,categories,args.refresh)
    elif args.command.lower() == "read":
        read_updates(args.name,args.all,categories)
    elif args.command.lower() == "clear":
        mark_as_read(args.name,categories)
        output.write_ok("Feeds cleared!")
    elif args.command.lower() == "start":
        if is_updater_running():
            output.write_info("Background updater already running!")
        else:
            try:
                start_background_updater()
            except Exception as e:
                output.write_error(f"Something went wrong when trying to run the updater: {e}")
    elif args.command.lower() == "stop":
        try:
            stop_background_updater()
        except IOError as e:
            output.write_info("Background updater is not running.")
    elif args.command.lower() == "import":
        if args.url == None:
            print("Usage: main.py import -u [OPML URL OR LOCAL PATH]")
        else:
            import_feeds(args.url)
    elif args.command.lower() == "help":
        sp.call(['less','-R',"README.md"])        
    else:
        parser.print_help()
else:
    parser.print_help()