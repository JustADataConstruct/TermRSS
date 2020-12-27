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

class TermRSS():   
    def __init__(self):
        self.feeds = {}
        self.config = {}
        self.parser = argparse.ArgumentParser(add_help=False,usage="Run termrss.py help to read the manual.")
        
        try:
            with open('config.json') as f:
                s = f.read()
                self.config = json.loads(s)
        except IOError:
            print("config file not found. Going back to defaults.")
            self.config["update_time_minutes"] = 10
            self.config["enable_color_output"] = True
            self.config["verbose_mode"] = False
            f = open('config.json','w')
            f.write(json.dumps(self.config,indent=4))
            f.close()

            
        self.output = OutputHelper(self.config["enable_color_output"])
        self.cache = CacheHelper(self.output,self.config)
        self.verbose = self.config["verbose_mode"]

        try:
            with open('feedinfo.json') as f:
                s = f.read()
                self.feeds = json.loads(s)
        except IOError as e:
            self.output.write_error("Feedinfo not found! Recreating it now.")
            initdate = str(datetime(1960,1,1,0,0,0))
            self.add_feed("Sample feed","https://www.feedforall.com/sample.xml","Test")

        self.parser.add_argument("command",choices=['help','update','read','add','remove','show','start','stop','import','clear'])
        self.parser.add_argument("-n","--name")
        self.parser.add_argument("-u","--url")
        self.parser.add_argument("-r","--refresh",action='store_true')
        self.parser.add_argument("--bg",action="store_true")
        self.parser.add_argument("-c","--categories")
        self.parser.add_argument("-f","--force-add",action="store_true")
        self.parser.add_argument("-a","--all",action="store_true")   
        self.parse_args(self.parser.parse_args())

    def parse_args(self,args):
        if args.bg:
            schedule.every(self.config["update_time_minutes"]).minutes.do(self.check_new_entries,to_console=False,force_refresh=False)
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
                    self.parser.print_help()
                else:
                    self.add_feed(args.name,args.url,categories,args.force_add)
            elif args.command.lower() == "remove":
                if args.name == None:
                    self.parser.print_help()
                else:
                    self.remove_feed(args.name)
                    self.output.write_ok("Feed removed!")
            elif args.command.lower() == "show":
                self.show_feeds(categories)
            elif args.command.lower() == "update":
                self.check_new_entries(True,categories,args.refresh)
            elif args.command.lower() == "read":
                self.read_updates(args.name,args.all,categories)
            elif args.command.lower() == "clear":
                self.mark_as_read(args.name,categories)
                self.output.write_ok("Feeds cleared!")
            elif args.command.lower() == "start":
                if self.is_updater_running():
                    self.output.write_info("Background updater already running!")
                else:
                    try:
                        self.start_background_updater()
                    except Exception as e:
                        self.output.write_error(f"Something went wrong when trying to run the updater: {e}")
            elif args.command.lower() == "stop":
                try:
                    self.stop_background_updater()
                except IOError as e:
                    self.output.write_info("Background updater is not running.")
            elif args.command.lower() == "import":
                if args.url == None:
                    print("Usage: termrss.py import -u [OPML URL OR LOCAL PATH]")
                else:
                    self.import_feeds(args.url)
            elif args.command.lower() == "help":
                sp.call(['less','-R',"README.md"])        
            else:
                self.parser.print_help()
        else:
            self.parser.print_help()

    def save_feed_file(self):
        """Saves changes made to the self.feeds dictionary to the feedinfo.json file.
        """
        if self.verbose:print("Trying to save file...")
        f = open('feedinfo.json','w')
        s = json.dumps(self.feeds,indent=4)
        f.write(s)
        if self.verbose:print("Saved.")
        f.close()

    def add_feed(self,feedname,feedURL,categories=[],force=False):
        """Adds a new feed to the self.feeds dictionary and saves it to file. Handles errors and
        restarting the updater.

        Args:
            feedname (string): Name to identify the feed.
            feedURL (string): The URL of the feed.
            categories (list of strings, optional): A string of categories separated by comma. Defaults to [].
            force (bool, optional): If True, will add the feed even if entries can't be detected. Defaults to False.
        """
        if feedURL.startswith(('http://','https://')) == False:
            if self.verbose:print("Checking if url has prefix...")        
            feedURL = "http://" + feedURL
        try:
            if self.verbose:print("Trying to parse feed...")
            f = feedparser.parse(feedURL)
        except Exception as e:
            self.output.write_error(f"Something went wrong when trying to parse this feed ({feedname}): {e}")
            return
        if len(f.entries) == 0 and force == False :
            self.output.write_error(f"No entries detected on feed {feedname}. Please make sure this URL is a valid feed. If you are sure the URL is correct, repeat the add command with the '-f' flag to forceadd it.")
            return
        etag = f.etag if hasattr(f,'etag') else ""
        modified = f.modified if hasattr(f,'modified') else ""
        initdate = str(datetime(1960,1,1,0,0,0))
        self.feeds[feedname.upper()] = {
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
            self.output.write_error(f"A problem was detected with your feed:{f.bozo_exception}. You may find problems when reading its entries. Do you want to add it? [Y]es/[N]o")
            answer = input()
            if answer.lower() == "n" or answer.lower() == "no":
                return
            
        self.save_feed_file()
        self.cache.save_cache_file(feedname,f)
        self.output.write_ok(f"Feed {feedname} added!") 
        if self.is_updater_running():
            #This is needed so the background process can reload the feed list. It's not pretty but it works.
            self.stop_background_updater(True)
            self.start_background_updater(True)

    def remove_feed(self,feedname):
        """Removes a feed from the self.feeds dictionary, removes that feed from the cache file, and
        saves the changes to disl.

        Args:
            feedname (string): Name of the feed to remove.
        """
        if self.feeds[feedname.upper()] !=None:
            if self.verbose:print("Feed exists, removing.")
            self.feeds.pop(feedname.upper())
            self.save_feed_file()
            self.cache.remove_from_cache(feedname)

    def check_new_entries(self,to_console=True,categories=[],force_refresh=False):
        """Tries to fetch new entries from the server. Calls check_cache_valid to handle the actual
        fetching and getting the latest version.

        Args:
            to_console (bool, optional): If true, will self.output to terminal. False when using the
            background process.. Defaults to True.
            categories (ist of strings, optional): String with a list of categories, separated by comma.. Defaults to [].
            force_refresh (bool, optional): If true, will tell check_cache_valid to download
            from the server even if there are no changes.. Defaults to False.
        """
        if to_console:
            self.output.write_info("Checking for new entries...")
        if len(categories) > 0:
            lst = [x for x in self.feeds if any(item in categories for item in self.feeds[x]["categories"])]
            if self.verbose:print("Filtering categories...")
        else:
            lst = self.feeds
            if self.verbose:print("Using main feed list.")
        for n in lst:
            if self.feeds[n]["valid"] == False:
                if to_console:
                    self.output.write_error(f"{n} is no longer valid and will not be updated. Please remove it from your list.")
                else:
                    sp.call(['notify-send',n,f"Invalid feed."])
                continue
            last_check = datetime.strptime(self.feeds[n]["last_check"],'%Y-%m-%d %H:%M:%S')
            self.cache.check_cache_valid(n,self.feeds[n],last_check,to_console,force_refresh)
            self.feeds[n]["last_check"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.save_feed_file()

    def read_updates(self,name,all = False,categories=[]): 
        """Grabs entries from cache and self.outputs them via the less command.

        Args:
            name (string): Name of the feed that wants to be read. If none, grabs all updated unless
            categories is not empty.
            all (bool, optional): If True, shows all self.feeds (categorized or existing). Defaults to False.
            categories (list of strings, optional): String with a list of categories separated
            by comma. Defaults to [].
        """
        text = ""
        if name != None and self.feeds[name.upper()] != None:
            if self.verbose:print("Trying to load from self.cache...")
            s = self.cache.load_from_cache(name)
            if s == None: return
            text = self.grab_entries(name,s)
        else:
            if len(categories) > 0:
                lst = [x for x in self.feeds if any(item in categories for item in self.feeds[x]["categories"])]
                if self.verbose:print("Filtering categories...")
            else:
                lst = self.feeds
                if self.verbose:print("Using main feed list...")
            if all == False:
                lst = [x for x in lst if self.feeds[x]["unread"] > 0]
                if len(lst) == 0:
                    text = "No new entries on any feed. Run read -a to see all past entries."
            for n in lst:
                s = self.cache.load_from_cache(n)
                if s == None: return
                text += self.grab_entries(n,s)
        text += "\n['Q' to exit]"
        with tempfile.TemporaryDirectory() as tmp:
            if self.verbose:print("Calling less")
            path = os.path.join(tmp,"rssentries")
            with open(path,"w") as o:
                o.write(text)
            sp.call(['less','-R',path])
        self.save_feed_file()

    def grab_entries(self,name,feed):
        """Returns a string with the feed's entries in a nice format.

        Args:
            name (string): Name of the feed.
            feed (dictionary): Actual feed object

        Returns:
            string: All entries requested.
        """
        lastread = datetime.strptime(self.feeds[name.upper()]["last_read"],'%Y-%m-%d %H:%M:%S') 
        url = self.feeds[name.upper()]["url"]
        s = self.output.write_feed_header(f"----[{name.upper()} - {url}]----") + "\n"    

        if self.verbose:print("Grabbing entries...")
        for e in feed["entries"]:
            p_date = datetime.fromtimestamp(time.mktime(time.struct_time(e["published_parsed"])))  
            desc = BeautifulSoup(e["summary"],'html.parser')
            new = True if p_date > lastread else False
            s += self.output.format_entry(name,e,desc.get_text(),new)
        self.feeds[name.upper()]["last_read"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')    
        self.feeds[name.upper()]["unread"] = 0
        return s              

    def show_feeds(self,categories = []):
        """self.outputs information from saved feeds.

        Args:
            categories (list of strings, optional): List of categories, separated by
            comma. If present, filters the result. Defaults to [].
        """
        if len(categories) > 0:
            lst= [x for x in self.feeds if any(item in categories for item in self.feeds[x]["categories"])]
        else:
            lst = self.feeds
        for n in lst:
            url = self.feeds[n]["url"]
            last_checked = self.feeds[n]["last_check"]
            last_read = self.feeds[n]["last_read"]
            unread = self.feeds[n]["unread"]
            valid = self.feeds[n]["valid"]
            categories = self.feeds[n]["categories"]
            self.output.write_info(f"{n}: {url}")
            print(f"Last checked: {last_checked}. Last read: {last_read}")
            print(f"Unread entries: {unread}")
            print(f"Categories: {categories}")
            if valid== False:
                self.output.write_error("WARNING: This feed is no longer valid and will not be updated.")
            print("\n")

    def import_feeds(self,source):
        """Tries to parse and import an opml file exported from another RSS reader. Will try
        to keep name and categories.

        Args:
            source (string): Path of the opml file.
        """
        result = listparser.parse(source)
        name = result.meta.title
        size = len(result.feeds)
        self.output.write_info(f"Do you want to import {size} feeds from {name}? [y]es/[n]o/[v]iew")
        answer = input()
        if answer.lower() == "v" or answer.lower() == "view":
            for i in result.feeds:
                print(f"{i.title} : {i.url}")
        elif answer.lower() == "y" or answer.lower() == "yes":
            try:
                for i in result.feeds:
                    if self.verbose:print(f"Trying to add {i.title}")
                    if len(i.categories) > 0:
                        if self.verbose:print("Grabbing categories")
                        categories = i.categories[0]
                    else:
                        categories = []
                    self.add_feed(i.title,i.url,categories)
            except Exception as e:
                self.output.write_error(f"Something went wrong when importing {i}!: {e}")
            finally:
                self.output.write_ok("Feeds imported successfully.")

    def mark_as_read(self,name,categories=[]):
        """Will update the last_read and unread properties of each feed to set them up to date and
        restart the background updater.

        Args:
            name (string): Name of the feed that wants to be cleared. If none, will apply to all feeds.
            categories (list of strings, optional): If present, will filter results.. Defaults to [].
        """
        if name != None and self.feeds[name.upper()] != None:
            feed = self.feeds[name.upper()]
            feed["last_read"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            feed["unread"] = 0
        else:
            if len(categories) > 0:
                lst = [x for x in self.feeds if any(item in categories for item in self.feeds[x]["categories"])]
            else:
                lst = self.feeds
            for f in lst:
                feed = self.feeds[f]
                feed["last_read"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                feed["unread"] = 0
        self.save_feed_file()
        if self.is_updater_running():
            self.stop_background_updater()
            self.start_background_updater()


    def start_background_updater(self,silent=False):
        """Will create the rssclient.pid file and start the background process. Time is self.configurable on the
        self.config.json file.

        Args:
            silent (bool, optional): [If True, will not print to terminal the status messages]. Defaults to False.
        """
        if self.verbose:print("Trying to start updater...")
        proc = sp.Popen(["python","termrss.py","show","--bg"])
        w = open("rssclient.pid","w")
        w.write(str(proc.pid))
        w.close()
        time = self.config["update_time_minutes"]
        if silent == False:
            if self.verbose:print("Done")
            self.output.write_ok(f"Background updater started successfully. Will check for new entries every {time} minute(s)")

    def stop_background_updater(self,silent=False):
        """Will try to remove the rssclient.pid file and stop the background process.

        Args:
            silent (bool, optional): If True, will not print to terminal the status messages. Defaults to False.
        """
        with open('rssclient.pid') as f:
            pid = f.read()
            os.kill(int(pid),9)
        os.remove('rssclient.pid')
        if silent == False:
            self.output.write_ok("Background updater stopped successfully.")
    def is_updater_running(self):
        return os.path.isfile("rssclient.pid")


TermRSS()