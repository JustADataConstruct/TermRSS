import feedparser

#Test feed
d = feedparser.parse('https://www.feedforall.com/sample.xml')
for e in d.entries:
    print(e.title)
    print(e.published)