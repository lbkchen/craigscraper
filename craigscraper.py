from lxml import html
import requests

URL = "https://sfbay.craigslist.org/search/apa?query=berkeley&search_distance=1&postal=94704&availabilityMode=0"

def get_listings():
    page = requests.get(URL)
    tree = html.fromstring(page.content)
    listings = tree.xpath('//li[@class="result-row"]')
    return listings

def get_single_node(node, path):
    data = node.xpath(path)
    assert len(data) != 0, "Extracted no data."
    assert len(data) == 1, "Extracted more than a single node."
    return data[0]

def get_info(listing):
    """Parses a listing a returns details of the listing in a dictionary."""

    price = get_single_node(listing, './a/span[@class="result-price"]/text()')
    date = get_single_node(listing, './p/time[@class="result-date"]').get('title')
    title = get_single_node(listing, './p/a[@class="result-title hdrlnk"]/text()')
    housing_info = listing.xpath('./p/span[@class="result-meta"]/span[@class="housing"]/text()')[0]
    housing_info = " ".join(housing_info.split())

    info = {
        "price"     : price,
        "date"      : date,
        "title"     : title,
        "housing"   : housing_info
    }

    print(info)
    return info

def main():
    listings = get_listings()
    get_info(listings[0])

if __name__ == "__main__":
    main()
