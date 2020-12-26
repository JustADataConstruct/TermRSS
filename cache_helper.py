import json
import os
import subprocess as sp
import time
from datetime import datetime

import feedparser

from output_helper import OutputHelper


class CacheHelper():
    def __init__(self,output_helper,config):
        """Handles loading and saving to and from the rsscache.json file and keeping the data up to date.

        Args:
            output_helper (OutputHelper object): An initialized OutputHelper instance. Used to print 
            status messages.
            config (object): A json object parsing the config.json file. 
        """
        self.output = output_helper
        self.config = config
        self.verbose = config["verbose_mode"]

    def save_cache_file(self,feedname,feed_content):
        """Tries to update the cached data of the indicated feed. If the cache file doesn't exist,
        will create it.

        Args:
            feedname (string): Name of the feed to update
            feed_content (object): Feed object to save.
        """
        if os.path.isfile('rsscache.json'):
            if self.verbose:print("Cache file exists")
            with open('rsscache.json') as f:
                cache = json.loads(f.read())
        else:
            if self.verbose:print("Cache file doesn't exist.")
            cache = {}
        cache[feedname.upper()] = feed_content
        if self.verbose:print("Writing cache file.")
        f = open('rsscache.json','w')
        f.write(json.dumps(cache,default=str,indent=4))
        f.close()

    def load_from_cache(self,feedname):
        """Tries to load the cached data for the indicated feed from the cache file. Will handle errors if
        the cache file is missing or the key can't be found.

        Args:
            feedname (string): Name of the feed to load.

        Returns:
            object: Json object with the feed data.
            None: If the file can't be found or there's no data for this feed.
        """
        try:
            with open('rsscache.json') as f:
                if self.verbose:print("Loading from cache")
                s = json.loads(f.read())[feedname.upper()]
        except FileNotFoundError:
            self.output.write_error("Cache file not found! Force an update (main.py update -r) to regenerate it.")
            return None
        except KeyError:
            self.output.write_error(f"Can't find feed {feedname} in cache file. Run update -r to regenerate it.")
            return None
        return s


    def remove_from_cache(self,feedname):
        """Tries to remove a feed's data from the cache file. Used when the user unsuscribes from a feed.

        Args:
            feedname (string): Name of the feed.
        """
        try:
            with open('rsscache.json') as f:
                cache = json.loads(f.read())
            if cache[feedname.upper()] != None:
                cache.pop(feedname.upper())
                with open('rsscache.json','w') as f:
                    f.write(json.dumps(cache,indent=4))
        except Exception as e:
            self.output.write_error(e)
   
    def check_cache_valid(self,name,feed,last_check,to_console,force_refresh):
        """Checks if has been enough time since the last time the server was called, tries to fetch
        new data from it if so, and handles the different HTML codes it can receive. Will update feedinfo
        and rsscache as needed to adjust to changes and updates. Will fail silently if it receives an
        unknown code.

        Args:
            name (string): Name of the feed to check.
            feed (object): Feed object to get data from.
            last_check (datetime): Datetime object with the last time the feed was checked for updates.
            to_console (bool): If True, will print status messages to terminal.
            force_refresh (bool): If True, will download new data from the server and refresh cache even if
            there are no changes.
        """
        etag = feed["etag"]
        modified = feed["last-modified"]
        diff = datetime.now() - last_check
        if diff.total_seconds()/60 < self.config["update_time_minutes"] and force_refresh == False: #If it's still too soon...
            if self.verbose:print("Update called too soon.")
            i = feed["unread"]
            if to_console:
                print(f"{name}: {i} unread")
            else:
                if i > 0:
                    sp.call(['notify-send',name,f"{i} unread"])            
            return
        #If not, we proceed:
        if self.verbose:print("Fetching server")
        result = feedparser.parse(feed["url"],etag=etag,modified=modified) if force_refresh == False else feedparser.parse(feed["url"])

        if result.status == 404:
            if to_console:
                self.output.write_error("Got an error 404 while trying to fetch this feed. Please check the URL is correct.")
            else:
                sp.call(['notify-send',name,"[ERROR] Error 404 received when fetching the feed."])
            return
        
        if result.status == 410: #Feed deleted.
            if to_console:
                self.output.write_error("This feed has been deleted from the server and will no longer be fetched. Please run remove to remove it from your list.")
            else:
                sp.call(['notify-send',name,"[ERROR] This feed has been deleted from the server and will no longer be fetched."])
            feed["valid"] = False
            return

        elif result.status == 301: #Permanent redirect
            if self.verbose:print("Updating url")
            new_url = result.href
            if to_console:
                self.output.write_info(f"This feed has been moved! URL has been updated to {new_url}. Please try updating again.")
            feed["url"] = new_url
            return

        elif result.status == 304: #No changes
            i = feed["unread"]
            if to_console:
                print(f"{name}: {i} unread")
            else:
                sp.call(['notify-send',name,f"{i} unread"])                
            return
        
        elif result.status == 200 or result.status == 302: #Either the web updated or it updated and it's a temporary redirect.
            if self.verbose:print(f"Status {result.status}")
            etag = result.etag if hasattr(result,'etag') else ""
            modified = result.modified if hasattr(result,'modified') else ""
            feed["etag"] = etag
            feed["last-modified"] = modified
            i = feed["unread"]
            for e in result.entries:
                if self.verbose:print("Checking for new entries")
                p_date = datetime.fromtimestamp(time.mktime(e.published_parsed))
                if p_date > last_check: #If newer.
                    i = i+1
            if to_console:
                print(f"{name}: {i} update(s)")
            else:
                if i > 0:
                    sp.call(['notify-send',name,f"{i} updates(s)"])      
            feed["unread"] = i     
            self.save_cache_file(name,result)
            return
