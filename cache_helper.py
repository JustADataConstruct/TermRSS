import json
import os
from datetime import datetime
import time
import subprocess as sp

from feedparser import FeedParserDict
import feedparser

from output_helper import OutputHelper


class CacheHelper():
    def __init__(self,output_helper,config):
        self.output = output_helper
        self.config = config

    def save_cache_file(self,feedname,feed_content):
        if os.path.isfile('rsscache.json'):
            with open('rsscache.json') as f:
                cache = json.loads(f.read()) #FIXME: Is there a way of appending without loading the whole file?
                f.close()
        else:
            cache = {}
        cache[feedname.upper()] = feed_content
        f = open('rsscache.json','w') #TODO: Is a json file the best way of doing this? Does it scale well?
        f.write(json.dumps(cache,default=str))
        f.close()

    def load_from_cache(self,feedname):
        with open('rsscache.json') as f:
            s = json.loads(f.read())[feedname.upper()]
            f.close()
        feed = FeedParserDict(s) #FIXME: Do we actually need this? We are always loading from cache.
        return feed


    def remove_from_cache(self,feedname):
        try:
            with open('rsscache.json') as f:
                cache = json.loads(f.read())
            if cache[feedname.upper()] != None:
                cache.pop(feedname.upper())
                with open('rsscache.json','w') as f:
                    f.write(json.dumps(cache))
        except Exception as e:
            self.output.write_error(e)
   
    def check_cache_valid(self,name,feed,last_check,to_console,force_refresh):
        etag = feed["etag"]
        modified = feed["last-modified"]
        diff = datetime.now() - last_check
        if diff.total_seconds()/60 < self.config["update_time_minutes"] and force_refresh == False: #If it's still too soon...
            print("too soon")
            i = feed["unread"]
            if to_console:
                print(f"{name}: {i} unread")
            else:
                if i > 0:
                    sp.call(['notify-send',name,f"{i} unread"])            
            return
        #If not, we proceed:
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
            etag = result.etag if hasattr(result,'etag') else ""
            modified = result.modified if hasattr(result,'modified') else ""
            feed["etag"] = etag
            feed["last-modified"] = modified
            i = feed["unread"]
            for e in result.entries:
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
