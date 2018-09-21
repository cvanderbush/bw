import io
import pandas as pd
from datetime import date, datetime, timedelta

import urllib3
import certifi
import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()

http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED',ca_certs=certifi.where())

out_dir = '/Users/carl/python/bradleywoods/rules/'

# create the url
url_beginning = 'https://www.federalregister.gov/documents/search.csv?conditions%5Bpublication_date%5D%5Bis%5D='
todays_date = date.today()
query_date = todays_date.strftime('%m/%d/%Y').replace('/','%2F')
file_date = todays_date.strftime('%Y-%m-%d')
url = url_beginning + query_date

# get a handle to the csv file
r = http.request('GET', url)

# load the csv data into a DataFrame
df = pd.read_csv(io.StringIO(r.data.decode('utf-8')))

# save the DataFrame to Excel
file_name = out_dir + 'fedregpubs-' + file_date + '.xlsx'
df.to_excel(file_name, index=False)
