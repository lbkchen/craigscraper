from lxml import html
import requests
import smtplib
import sched, time
import re

URL = "https://sfbay.craigslist.org/search/apa?query=berkeley&search_distance=1&postal=94704&availabilityMode=0"

def get_listings():
    page = requests.get(URL)
    tree = html.fromstring(page.content)
    listings = tree.xpath('//li[@class="result-row"]')
    return listings

def parse_price(price_str):
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    if len(price_str) == 0:
        return 0
    elif price_str[0] == "$":
        return int(price_str[1:])
    elif not is_number(price_str):
        print("Price is not a number")
        return 0
    else:
        return int(price_str)

def get_single_node(node, path):
    data = node.xpath(path)
    # assert len(data) != 0, "Extracted no data."
    if isinstance(data, str):
        return data
    elif isinstance(data, int):
        return data
    elif isinstance(data, list):
        if len(data) == 0:
            print("Extracted no nodes. Returning empty string.")
            return ""
        if len(data) > 1:
            print("Extracted multiple nodes, using first.")
            return data[0]
    return data[0]

def get_info(listing):
    """Parses a listing a returns details of the listing in a dictionary."""

    price = parse_price(get_single_node(listing, './a/span[@class="result-price"]/text()'))

    date = get_single_node(listing, './p/time[@class="result-date"]').get('title')

    title = get_single_node(listing, './p/a[@class="result-title hdrlnk"]/text()')

    housing_info = listing.xpath('./p/span[@class="result-meta"]/span[@class="housing"]/text()')
    if housing_info:
        housing_info = " ".join(housing_info[0].split())

    info = {
        "price"     : price,
        "date"      : date,
        "title"     : title,
        "housing"   : housing_info
    }

    print(info)
    return info

def get_matching_listings(listings):
    listings = get_listings()
    listings = [get_info(listing) for listing in listings]

    # Condition: if price < $5000
    filter_price = lambda listing: listing["price"] < 5000

    # Condition: at least 2 BR
    filter_bed = lambda listing: re.search(r'2\s?br', listing["housing"], re.M|re.I)

    filters = [
        filter_price,
    ]

    return [listing for listing in listings if all([f(listing) for f in filters])]

def stringify_list(lst, sep="\n"):
    return sep.join(str(e) for e in lst)

def sendEmail(sc):
    matching_listings = get_matching_listings(get_listings())[0]
    # matching_listings = stringify_list(matching_listings)
    print(matching_listings)
    sender_email = "yourpokemongopal@gmail.com"
    sender_password = "pokemongo"
    email_list = [
        "lbkchen@gmail.com",
        "jeromejsun@gmail.com",
        "a.yeung@berkeley.edu"
    ]
    subject = "MATCH FOUND in Craigslist for Housing"

    print("Preparing to send email...")
    server = smtplib.SMTP("smtp.gmail.com:587")
    server.ehlo()
    server.starttls()
    server.login(sender_email, sender_password)
    for email in email_list:
        msg = "\n".join([
            "From: %s" % sender_email,
            "To: %s" % email,
            "Subject: %s" % subject,
            ""]) + "\n" + ("Dearest Comrade, I am pleased to report that the following listings near you have matched your preferences: \n%s." % matching_listings) + \
            "\n\nBest,\nYour Craigslist Bro"
        server.sendmail(sender_email, email, msg)
    print("Sent emails to:", ", ".join(email_list))
    server.quit()
    sc.enter(600, 1, sendEmail, (sc,))

def main():
    s = sched.scheduler(time.time, time.sleep)
    s.enter(1, 1, sendEmail, (s,))
    s.run()

if __name__ == "__main__":
    main()
