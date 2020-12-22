import colorama

class OutputHelper():
    def __init__(self,enableColor : bool):
        self.color = enableColor
        if enableColor:
            colorama.init(autoreset=True)

    def write_feed_header(self,msg):
        if self.color:
            msg = colorama.Back.CYAN + colorama.Fore.BLACK + msg
        print(msg)

    def write_feed_entry(self,msg):
        if self.color:
            msg = colorama.Style.BRIGHT + msg
        print(msg)

    def write_feed_link(self,msg):
        if self.color:
            msg = colorama.Fore.BLUE + msg
        print(msg)

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