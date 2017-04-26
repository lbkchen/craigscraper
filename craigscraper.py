from lxml import html
import requests
import smtplib
import sched, time
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


URL = "https://sfbay.craigslist.org/search/apa?query=berkeley&search_distance=1&postal=94704&availabilityMode=0"
DEBUG = False


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
        except (ValueError, TypeError):
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


def decode_node(node):
    return node.encode('ascii', 'ignore').decode('utf-8')


def get_single_node(node, path, decode=False):
    data = node.xpath(path)
    if isinstance(data, str):
        return data.encode('utf-8')
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
    elif decode:
        return decode_node(data)
    return data


def stringify_list(lst, sep="<br>"):
    lst = [decode_node(node).strip() for node in lst]
    lst = [s for s in lst if s]
    return sep.join(lst)


def get_info(listing):
    """Parses a listing a returns details of the listing in a dictionary."""

    price = parse_price(get_single_node(listing, './a/span[@class="result-price"]/text()'))

    date = get_single_node(listing, './p/time[@class="result-date"]').get('title')

    title = get_single_node(listing, './p/a[@class="result-title hdrlnk"]/text()', decode=True)

    link = get_single_node(listing, './a[@class="result-image gallery"]')
    link = link.get('href') if len(link) > 0 else link
    link = "https://sfbay.craigslist.org" + link

    # Stuff in inner page
    try:
        inner_page = requests.get(link)
        inner_tree = html.fromstring(inner_page.content)
        description = stringify_list(inner_tree.xpath('//*[@id="postingbody"]/descendant-or-self::*/text()'))

        details = inner_tree.xpath('//p[@class="attrgroup"]/descendant-or-self::*/text()')
        details = stringify_list(details, sep=", ")

        inner_info = {
            "description"   : description,
            "details"       : details
        }
    except OSError as e:
        inner_info = {}
        print("Link doesn't exist: " + str(e))

    info = {
        "price"         : price,
        "date"          : date,
        "title"         : title,
        "link"          : link,
    }
    info.update(inner_info)

    return info


def get_matching_listings(listings, max_num=10):
    listings = [get_info(listing) for listing in listings]
    temp = []
    for i in range(min(max_num, len(listings))):
        temp += [listings[i]]
    listings = temp

    # Condition: if price < $5000
    filter_price = lambda listing: listing["price"] < 5000 and listing["price"] > 2500

    # Condition: at least 2 BR
    filter_bed = lambda listing: re.match(r'(2|3|4)\s*br', listing["details"], re.M|re.I) is not None

    # Condition: at least 2 BA
    filter_bath = lambda listing: re.match(r'(2|3)\s*ba', listing["details"], re.M|re.I) is not None

    filters = [
        filter_price,
        filter_bed,
        filter_bath, 
    ]

    return [listing for listing in listings if all([f(listing) for f in filters])]


def render_result(result):
    """Returns html where `result` is a listing dictionary."""
    rendered = ""
    for key, value in result.items():
        rendered += "<b style='font-size=14px'>%s</b>: %s<br>" % (key, value)
    return rendered

def sendEmail(sc, debug=True):
    if debug:
        matching_listings = get_matching_listings([get_listings()[0]])
    else:
        matching_listings = get_matching_listings(get_listings())
    sep = "<br><br><br><br>----------<<-------------------------------------------------------------->>----------<br><br><br><br>"
    rendered_listings = sep.join(list(map(render_result, matching_listings)))

    sender_email = "yourpokemongopal@gmail.com"
    sender_password = "pokemongo"
    email_list = [
        "lbkchen@gmail.com",
        # "jeromejsun@gmail.com",
        # "a.yeung@berkeley.edu",
    ]
    subject = "MATCH FOUND in Craigslist for Housing"

    if debug:
        print("Matching listings:\n\n" + rendered_listings)
        return

    print("Preparing to send email...")
    server = smtplib.SMTP("smtp.gmail.com:587")
    server.ehlo()
    server.starttls()
    server.login(sender_email, sender_password)
    for email in email_list:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = email
        html = """\
        <html>
          <head></head>
          <body>
            <p>
                <b style='font-size:18px'>Dearest Comrade</b>,<br><br>
                I am <b>pleased</b> to report that the following listings near you have matched your varied preferences:<br>
            </p>

            %s

            <p>
                Best,<br>
                <b style='font-size:18px'>Your Craigslist Brobot ♥</b>
            </p>
          </body>
        </html>
        """ % rendered_listings
        msg.attach(MIMEText(html, 'html'))
        server.sendmail(sender_email, email, msg.as_string())
    print("Sent emails to:", ", ".join(email_list))
    server.quit()
    sc.enter(600, 1, sendEmail, (sc, DEBUG))


def main():
    s = sched.scheduler(time.time, time.sleep)
    s.enter(1, 1, sendEmail, (s, DEBUG))
    s.run()


if __name__ == "__main__":
    main()
