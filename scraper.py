import re
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup
import shelve

stopwords = ["a", "about", "above", "after", "again", "against", "all",
            "am", "an", "and", "any", "are", "aren\'t", "as", "at", "be",
            "because", "been", "before", "being", "below", "between", "both",
            "but", "by","can\'t","cannot", "could", "couldn\'t", "did",
            "didn\'t", "do", "does", "doesn\'t", "doing", "don\'t", "down",
            "during", "each", "few", "for", "from", "further", "had", "hadn\'t",
            "has","hasn\'t","have", "haven\'t", "having","he","he\'d","he\'ll",
            "he\'s", "her", "here", "here\'s", "hers", "herself", "him", "himself",
            "his", "how","how\'s", "i", "i\'d", "i\'ll", "i\'m", "i\'ve", "if",
            "in", "into", "is", "isn\'t", "it", "it\'s", "its", "itself",
            "let\'s", "me", "more", "most", "mustn\'t", "my", "myself", "no",
            "nor", "not", "of", "off", "on", "once", "only", "or", "other",
            "ought", "our", "ours", 'ourselves', 'out', 'over', 'own', 'same', 
            "shan't", 'she', "she'd", "she'll", "she's", 'should', "shouldn't", 
            'so', 'some', 'such', 'than', 'that', "that's", 'the', 'their', 
            'theirs', 'them', 'themselves', 'then', 'there', "there's", 'these', 
            'they', "they'd", "they'll", "they're", "they've", 'this', 'those', 
            'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', "wasn't", 
            'we', "we'd", "we'll", "we're", "we've", 'were', "weren't", 'what', "what's", 
            'when', "when's", 'where', "where's", 'which', 'while', 'who', "who's",
            'whom', 'why', "why's", 'with', "won't", 'would', "wouldn't", 'you',
            "you'd", "you'll", "you're", "you've", 'your', 'yours', 'yourself', 'yourselves']

def scraper(url, resp):
    links = extract_next_links(url, resp)

    if (resp.status >= 200) and (resp.status <= 399):
        # if valid status code returned (URL can be parsed)
        # get HTML content from current link
        if not resp.raw_response:
            print("Empty page. Scraping for this URL canceled")
            return links

        url_html = BeautifulSoup(resp.raw_response.content, 'html.parser')

        # check meta tags, see if page allows scraping
        metatag = url_html.find('meta', attrs={"name":"robots", "content":"noindex"})
        if metatag:
            return links

        # tokenize text
        url_text = url_html.get_text()
        tokens = tokenize(url_text)
        token_dict = compute_token_freq(tokens)

        # check for low-info (lower bound) + high info (upper bound)
        # if num of UNIQUE tokens < 100, page is too low-info
        # if num of UNIQUE tokens > 1,000, page is too high-info
        if (len(token_dict) < 100) or (len(token_dict) > 1000):
            return links

        # else, get URLs from all hyperlinks:
        # access 'href' (full link)
        links = [link.get('href') for link in url_html.find_all('a') if link.get('rel') != 'nofollow']

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

            # get current token:frequency dict for all pages
            # and update the dict's frequency total
            all_tokens = token_dict
            if "tokendict" in site_shelf:
                all_tokens = update_tkdict(site_shelf["tokendict"], token_dict)

            # put data back
            site_shelf["stats"] = curr_stats
            site_shelf["tokendict"] = all_tokens

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

        if parsed.scheme not in set(["http", "https"]):
            return False
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
            return False
        # check for valid domain
        if not re.match(r"(.*\.)?(ics|stat|informatics|cs)+(.uci.edu)$", parsed.netloc.lower()):
            return False
        # check for calendar format in URL path OR query (YYYY-MM-DD) and (YYYY-MM)
        if re.match(r".*[0-9]{4}-[0-9]{2}(-[0-9]{2})?.*", parsed.path) or re.match(r".*[0-9]{4}-[0-9]{2}(-[0-9]{2})?.*", parsed.query):
            return False
        # block pages that have a search bar + applicable filters
        if "filter" in parsed.query:
            return False
        # block pages that have a login
        if "login" in parsed.path:
            return False

        # all filters passed
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

def update_tkdict(main_dict, add_dict)->dict:
    """Combine two token dictionaries and their token frequencies."""
    for token, freq in add_dict.items():
        if token in main_dict:
            main_dict[token] = main_dict[token] + freq
        elif not(token in stopwords):
            main_dict[token] = freq

    return main_dict