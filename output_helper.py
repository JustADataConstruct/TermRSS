import colorama

class OutputHelper():
    def __init__(self,enableColor : bool):
        self.color = enableColor
        if enableColor:
            colorama.init(autoreset=True)

    def format_entry(self,name,entry,desc,new):
        # s = s + e["title"] + "\n"
        # s = s + e["link"] + "\n"
        # #s = s + descriptionsoup.get_text() + "\n"
        # s = s + e["published"] + "\n\n"

        s = self.write_feed_entry(entry["title"],new)

        s = s + self.write_feed_link(entry["link"])
        s = s + self.write_feed_description(desc,new)
        s = s + self.write_feed_description(entry["published"]) + "\n\n"
        
        return s

    def write_feed_header(self,msg):
        if self.color:
            msg = colorama.Back.CYAN + colorama.Fore.BLACK + msg
        return msg + "\n"

    def write_feed_entry(self,msg,is_new=False):
        if is_new:
            alert = colorama.Back.CYAN + colorama.Fore.BLACK + " [NEW] " + colorama.Back.RESET + colorama.Fore.RESET
            msg = alert + msg
            if self.color:
                msg = colorama.Style.BRIGHT + msg
        return msg + "\n"

    def write_feed_description(self,msg,is_new=False):
        if self.color:
            if is_new == False:
                msg = colorama.Style.DIM + msg
        return msg + "\n"

    def write_feed_link(self,msg):
        if self.color:
            msg = colorama.Fore.BLUE + msg
        return msg + "\n"

    def write_error(self,msg):
        if self.color:
            msg = colorama.Fore.RED + msg
        print(msg)

    def write_ok(self,msg):
        if self.color:
            msg = colorama.Fore.GREEN + msg
        print(msg)

    def write_info(self,msg):
        if self.color:
            msg = colorama.Fore.YELLOW + msg
        print(msg)