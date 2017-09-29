from bs4 import BeautifulSoup
import urllib2
import pprint
import json, os, re
from pymongo import MongoClient

client = MongoClient()
db = client.sunscreen

user_agent = 'User-Agent'
site_header = 'AmyCrawler/1.0 +http://amyqian.org/'
opener = urllib2.build_opener()
website_prefix = 'http://www.ewg.org'
toDo_page_urls = []
completed_urls = []
products = {}

def getProductLabelLink(product, url):
    product_url = url
    r = urllib2.Request(product_url)
    r.add_header(user_agent, site_header)

    data = opener.open(r).read()
    soup = BeautifulSoup(data, "html.parser")

    page_html = soup.find('li', attrs={"title": "Warnings_and_Directions"})

    return product_url + page_html.a['href']

def getProductLabelInfo(product, url):
    label_url = url
    r = urllib2.Request(label_url)
    r.add_header(user_agent, site_header)

    data = opener.open(r).read()
    soup = BeautifulSoup(data, "html.parser")

    first_link = soup.find('div', id="Warnings_and_Directions")
    ingredients_html = first_link.find_next("p")

    return ingredients_html.get_text()

def parseSPF(product, name):
    spf = 'unknown'
    if 'SPF' in name:
        lhs, rhs = name.split('SPF', 1)
    
        if 'ormulation' in rhs:
            spf = rhs[1:3]
        else:
            spf = rhs

    product['spf'] = spf

def parseIngredients(product, ingr):
    # parses ingr with punctuation
    all_ingr = re.split('\.\D|\, |\: |\; ', ingr)
    active = {}
    inactive = []
    active_ingr = ''
    active_perc = 0
    trash = []

    for i in all_ingr:
        lower_case = i.lower()
        if 'active' in lower_case or 'inactive' in lower_case:
            if len(i.split()) > 4:
                pass
            else:
                trash.append(i)

        # if active ingr string
        if '%' in i:
            strings = i.split(')')
            # split string into individual words
            splits = strings[0].split()
            
            # if there is a digit in the word, that is the percentage
            # else, that is the part of the ingr name
            for s in splits:
                if bool(re.search(r'\d', s)) and '.' in s:
                    active_perc = re.search(r"[-+]?\d*\.\d+|\d+", s).group()
                elif bool(re.search(r'\d', s)):
                    active_perc = re.search(r'\d+', s).group()
                else:
                    active_ingr += s + ' '
            # add entry to active ingr dictionary
            active[active_ingr] = active_perc
            active_ingr = ''
        else:
            inactive.append(i)

        # remove da trash
    for t in trash:
        if t in inactive:
            inactive.remove(t)


    product['active_ingredients'] = active
    product['inactive_ingredients'] = inactive

    

def getProductInfo(url):
    # construct request with site user agent header
    
    r = urllib2.Request(url)
    r.add_header(user_agent, site_header)

    # make da soup
    search_data = opener.open(r).read()
    soup = BeautifulSoup(search_data, "html.parser")

    # get HTML table info of products
    product_names = soup.find_all('td', class_='product_name_list')

    first_link = soup.find('div', class_="light")
    second_link = first_link.find('a')
    rest_links = second_link.find_next_siblings('a')
    rest_links.append(second_link)

    # add current url and nav bar urls to all urls, IF they don't exist in completed urls

    for item in rest_links:
        item_url = website_prefix + item['href']
        if item_url not in completed_urls and item_url not in toDo_page_urls:
            toDo_page_urls.append(item_url)

    # get product names and links to product page
    for name in product_names:
        product_name = name.a.get_text()
        products[product_name] = {}
        product_page_url = website_prefix + name.a['href']
        product_label_link = getProductLabelLink(products[product_name], product_page_url)
        ingr = getProductLabelInfo(products[product_name], product_label_link)

        # parse SPF, active ingredient, and inactive ingredients and add them to product dict
        parseSPF(products[product_name], product_name)
        parseIngredients(products[product_name], ingr)

        db.p.insert({ product_name : products[product_name] }, check_keys=False)

    # add current url to completed_urls, and current iteration of products to all_products
    completed_urls.append(url)

    pprint.pprint(len(products))

if __name__ == "__main__":
    os.chdir("/Users/amyqian/Documents/sunscreen")

    base_url = 'http://www.ewg.org/skindeep/browse.php?atatime=50&category=sunscreen%3A_SPF_15-30&&showmore=products&start=0'
    toDo_page_urls.append(base_url)

    for url in toDo_page_urls:
        getProductInfo(url)

    print 'Done!'




