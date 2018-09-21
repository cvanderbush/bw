import io, os, shutil
import zipfile
from bs4 import BeautifulSoup
import lxml
import pandas as pd
from datetime import date, datetime, timedelta

import urllib3
import certifi
import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()

# see urllib3 docs here https://urllib3.readthedocs.io/en/latest/user-guide.html
http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',ca_certs=certifi.where())

yesterday = date.today() - timedelta(1)
pdate = yesterday.strftime('%Y-%m-%d')
entity_list = ['hres', 'sres', 'hconres', 'sconres', 'hjres', 'sjres', 'hr', 's']
url_front = 'https://www.gpo.gov/fdsys/bulkdata/BILLSTATUS/115/'
url_mid = '/BILLSTATUS-115-'
url_end = '.zip'
out_dir = '/Users/carl/python/bradleywoods/bills'
zipdir = out_dir + '/billzips-' + pdate

# create zip directory only if it doesn't exist
try:
    os.makedirs(zipdir)
except FileExistsError:
    pass

df_bills = pd.DataFrame()

# loop for the 8 entities in the bulk data archive
for entity in entity_list:


    z_name = zipdir + url_mid + pdate + '-' + entity + url_end

    # first check if the zip file has already been downloaded
    try:
        z = zipfile.ZipFile(z_name)  # if it has, attach to it
    except IOError:  # if it doesn't exist, download it

        # construct the url
        url = url_front + entity + url_mid + entity + url_end
        # print(url)

        # get a handle to the zip file
        r = http.request('GET', url)

        # first, save the zip file
        f = open(z_name, 'wb')  # prepare a file to write to in binary mode
        bytes_written = f.write(r.data)  # r.data is urllib3 library's way of representing the contents received back from the request
        f.close()

        # attach to the zip file based on the data
        z = zipfile.ZipFile(io.BytesIO(r.data))

    xmlfiles = z.namelist()


    # takes about 3 min to run for 3000 entries
    records = []  # list to collect dicts of records
    for f in xmlfiles:
        page = z.read(f)
        soup = BeautifulSoup(page, 'xml')

        # create billid
        billid = '-'.join([soup.congress.text, soup.billType.text, soup.billNumber.text])

        #find title
        title = soup.bill.title.text

        # find introduced date
        intro = soup.introducedDate.text

        # find sponsor
        try:
            sponsor = soup.sponsors.item.fullName.text
        except:
            sponsor = "None found"

        # find last action date
        try:
            action_date = soup.latestAction.actionDate.text

        except:
            action_date = soup.introducedDate.text

        # find last action
        try:
            action = soup.latestAction.find('text').text
        except:
            action = "None found"

        # find policyArea if one exists to create policy
        try:
            policy = soup.policyArea.contents[1].text
        except:
            policy = 'No listed policy'

        # create list of legislative subjects if they exist
        try:
            ls = soup.legislativeSubjects.find_all('item')
            subj_list = []
            subjects = 'No subjects defined'
            for entry in ls:
                entry = str(entry)  # need to convert from bs4 object to string
                clean = entry.split('<name>')[1].split('</name>')[0]
                subj_list.append(clean)
                subjects = '; '.join(subj_list)  # convert from list to semi-colon separated string
        except:
            subjects = 'No subjects defined'

        # create the record dict
        items = {'billid':billid, 'title':title, 'introDate':intro, 'sponsor':sponsor,
                 'lastActionDate':action_date, 'lastAction':action, 'policy':policy, 'subjects': subjects}
        # append the record to the list
        records.append(items)

    df_bills = df_bills.append(records, ignore_index = True)
    # print(entity, '{:,}'.format(bytes_written)) - commenting this because bytes not written if file previously existed
    print(entity)

# dict order is unpredictable so need to reindex df to get the columns in the order we want
df_bills=df_bills.reindex(columns=['billid', 'title', 'introDate', 'sponsor', 'lastActionDate', 'lastAction', 'policy', 'subjects'])

df_bills['la_days'] = [(datetime.strptime(x, '%Y-%m-%d') - datetime(2017,1,1)).days for x in df_bills.lastActionDate]

filename = out_dir + '/df_bills-' + date.today().strftime('%Y-%m-%d') + '.msgpack'
df_bills.to_msgpack(filename)

today = (date.today() - date(2017,1,1)).days
one_day = today - 1
one_week = today - 7
two_weeks = today - 14
one_month = today - 30
two_months = today - 60
three_months = today - 90
six_months = today - 180
daybins = [0, six_months, three_months, two_months, one_month, two_weeks, one_week, one_day]

holderdf = pd.DataFrame()
for p in sorted(set(df_bills.policy)):
    cut = pd.cut(df_bills[df_bills.policy == p].la_days, daybins, labels = ['6M', '3M', '2M', '1M', '2W', '1W', '1D'] )
    tally = pd.value_counts(cut, sort = False)
    holderdf[p] = tally

filename = out_dir + '/holderdf-' + date.today().strftime('%Y-%m-%d') + '.msgpack'
holderdf.to_msgpack(filename)

newbills=df_bills[df_bills.introDate==pdate]
newbills=newbills.drop('la_days', axis=1)
newactions=df_bills[(df_bills.lastActionDate==pdate) & (df_bills.introDate != pdate)]
newactions=newactions.drop('la_days', axis=1)
newbills.to_excel(out_dir + '/newbills-' + pdate + '.xlsx', index=False)
newactions.to_excel(out_dir + '/newactions-' + pdate + '.xlsx', index=False)
