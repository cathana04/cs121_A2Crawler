import re
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup
import shelve

# git log
# Added HTML parsing of url content, url defragment + assembly, and additional conditions in url validation.
# Added tokenizer, token dictionary creation, basic low/high info checks, and calendar check in is_valid()

# stopword list
stopwords = []

def scraper(url, resp):
    # links = extract_next_links(url, resp)
    links = []
    print("scraping", url)

    if (resp.status >= 200) and (resp.status <= 399):
        # if valid status code returned (URL can be parsed),
        # check if robots.txt file allows scraping (EC)
        print("STATUS:", resp.status) # DEBUG

        # get HTML content from current link
        if not resp.raw_response:
            print("Empty page. Scraping for this URL canceled")
            return links

        url_html = BeautifulSoup(resp.raw_response.content, 'html.parser')

        # tokenize text
        url_text = url_html.get_text()
        tokens = tokenize(url_text)
        token_dict = compute_token_freq(tokens)

        print("unique token count:", len(token_dict)) # DEBUG

        # check for low-info (lower bound) + high info (upper bound)
        # if num of UNIQUE tokens < 100, page is too low-info
        # if num of UNIQUE tokens > 1,000, page is too high-info
        if (len(token_dict) < 100) or (len(token_dict) > 1000):
            print("bounds reached")
            return links
        
        # check for near-duplicate pages (EC)

        # else, get URLs from all hyperlinks:
        # access 'href' (full link)
        links = [link.get('href') for link in url_html.find_all('a')]
        
        #with open('linkinfo.txt', 'a') as d:
            #d.write(url)
            #d.write(" GENERATED THE FOLLOWING: ---------------------\n")
            #for link in links:
                #if link:
                    #d.write(link)
                    #d.write('\n')

        # and shelve current URL data (token_dict)
        with shelve.open("sitedata") as site_shelf:
            
            # add URL and its token dict
            site_shelf[url] = token_dict

            # get current shelf data
            curr_stats = {"longest_page": (0, "NULL"),}
            if "stats" in site_shelf:
                curr_stats = site_shelf["stats"]

            # edit longest page record
            if len(tokens) > curr_stats["longest_page"][0]:
                newstats = (len(tokens), url)
                curr_stats["longest_page"] = newstats

            # put data back
            site_shelf["stats"] = curr_stats

    else:
        print("URL could not be parsed due to bad status code: ", resp.status)
    
    # return scraped URLs as long as they are validated
    # defragment and reassemble each URL
    return [urlunparse((urlparse(link))._replace(fragment="")) for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    return list()

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)

        #par = open("parsing.txt", 'a') # DEBUG
        #if parsed:
            #par.write("PARSED URL: ")# DEBUG
            #par.write(str(parsed))
            #par.write('\n')

        if parsed.scheme not in set(["http", "https"]):
            # par.write("failed scheme check.\n")
            # par.close()
            return False
        # return not re.match(
        # check for non-website URLS
        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv|xml"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()):
            # xml bad.
            # par.write("path check failed.\n")
            # par.close()
            return False
        # check for valid domain
        if not re.match(
            # r".*ics|.*stat|.*informatics|.*cs" + r"uci.edu$", parsed.netloc.lower()):
            r".*(ics|stat|informatics|cs)+(.uci.edu)$", parsed.netloc.lower()):
            # par.write("domain check failed.\n")
            # par.close()
            return False
        # check for calendar format in URL (YYYY-MM-DD) and (YYYY-MM)
        if re.match(r".*[0-9]{4}-[0-9]{2}(-[0-9]{2})?.*", parsed.path):
            # par.write("calendar check failed.\n")
            # par.close()
            return False

        # all filters passed
        # par.write("link passes.\n")
        # par.close()
        return True

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def tokenize(textfile) -> list:
    """Split a string of text into a list of tokens."""

    token_list = []

    lines = textfile.splitlines()

    for line in lines:
        # split by any non-alphanumeric character, excluding (')
        delims = re.compile(r'[^a-zA-Z0-9\']+')
        tokens = delims.split(line)

        for token in tokens:
            # if not empty token
            if token: 
                token_list.append(token.lower())

    return token_list

def compute_token_freq(tokens:list) -> dict:
    """Given a list of tokens, computes the frequency at which
        each token appears in a text file. Returns a dict with
        each token string mapped to its frequency."""
    
    freq_dict = {}

    for token in tokens:
        if token in freq_dict:
            # add to existing token count
            freq_dict[token] = freq_dict[token] + 1
        else:
            # start token:freq count with 1
            freq_dict[token] = 1

    return freq_dict

def common_word_count(frequencies:dict):
    filtered_tokens = {}

    for token, freq in frequencies.items():
        if not (token in stopwords):
            filtered_tokens[token] = freq

    freqlist = frequency_sort(filtered_tokens)

def frequency_sort(frequencies:dict):
    """Sort a dictionary of token:freq pairs by descending frequency + alphabetically to break ties. 
       Returns a list of tuples (freq, token)."""
    
    freqlist = []
    # create tuples (frequency, token) of each token:frequency pair
    for word, freq in frequencies.items():
        freqlist.append(tuple([freq, word]))
    
    # sort list of tuples
    freqlist_sort1 = sorted(freqlist)
    freqlist_sorted = sorted(freqlist_sort1, key = lambda tk: tk[0], reverse = True)

    return freqlist_sorted
