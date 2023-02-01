# def main(request, context):
import imaplib
import email
from bs4 import BeautifulSoup
import re
import datetime
from fuzzywuzzy import fuzz
import requests
import pytz
# https://towardsdatascience.com/generating-a-requirements-file-jupyter-notebook-385f1c315b52

# initializing dictionary
payee_dict = {
    'Self Maintenance': ['xx', 'xx'],
    'Home Maintenance': ['xx'],
    'Eating Out':       ['xx', 'xx', 'restaurant', 'food'],
    'Groceries':        ['grocery', 'xx'],
    'Petrol':           ['transport', 'xx'],
    'Reimbursement':    ['refund', 'reverse', 'reimbursement', 'reversal', ''],
    'Salary':           [''],
    'Software Apps':    ['apple services'],
    'Taxi':             ['uber', 'taxi']
}
#xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx will be in your URL when u open your YNAB category
category_dict = {
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx': ['Self Maintenance'],
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx': ['Home Maintenance'],
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx': ['Eating Out'],
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx': ['Groceries'],
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx': ['Petrol'],
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx': ['Salary'],
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx': ['Software Apps'],
    'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx': ['Taxi']
}

# Connection with GMAIL using SSL
my_mail = imaplib.IMAP4_SSL('imap.gmail.com')
my_mail.login("yourmail@gmail.com", "password")
my_mail.select('"inbox"')


def get_msg_numbers(mail_ids):
    outputs = []
    for mail_id in mail_ids:
        response = my_mail.search(None, 'FROM', mail_id)
        try:
            outputs.extend(response[1][0].split())
        except:
            None
    return outputs


mail_id_list = get_msg_numbers(
    ['xxx@bank.com', 'xxx@bank.net'])
print(mail_id_list)

msgs = []
for num in mail_id_list:
    typ, data = my_mail.fetch(num, '(RFC822)')
    msgs.append(data)

body=[]
subject=[]
froms=[]
email_time=[]
# now = datetime.datetime.utcnow().replace(tzinfo=None)
for msg in msgs[::-1]:
    for response_part in msg:
        if type(response_part) is tuple:
            my_msg=email.message_from_bytes((response_part[1]))
            print ("subj:", my_msg['subject'])
            subject.append(my_msg['subject'])
            print ("from:", my_msg['from'])
            froms.append(my_msg['from'])
            time_string = re.search(r'(.*\+\d{4})', my_msg.get("Date")).group(1)
            email_datetime = datetime.datetime.strptime(time_string, '%a, %d %b %Y %H:%M:%S %z').astimezone(pytz.timezone('Asia/Kolkata'))
            print (email_datetime.strftime('%d %b %Y %I:%M:%S %p'))
            # print(my_msg.get("Date"))
            email_time.append(email_datetime)
            if my_msg.is_multipart():
                for part in my_msg.get_payload():
                    # body.append(payload)
                    body.append(part.get_payload(decode=True).decode('utf-8'))
            else:
                body.append(my_msg.get_payload(decode=True).decode('utf-8'))
body_strings = []
for i in body:
    soup = BeautifulSoup(i, 'html.parser')
    res = soup.find('body').text
    # print(res)
    body_strings.append(res)

# Sending Data to YNAB
# Get YNAB budget_id and accesstoken from your YNAB settings
endpoint = 'https://api.youneedabudget.com/v1/budgets/'
budget_id = 'xyz'
access_token = 'xyz'
headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {access_token}'
}

def multiple(words):
    if any(word in words for word in ["credited", "refund", "reversed"]):
        multiple = 1
    else:
        multiple = -1
    return(multiple)

def search_dict(payee_dict, search_term):
    if search_term is None:
        return 'None'
    match_key = None
    match_percentage = 60
    for key, values in payee_dict.items():
        for value in values:
            if value:
                percentage = fuzz.ratio(value, search_term)
                if percentage > match_percentage:
                    match_percentage = percentage
                    match_key = key
    return match_key

#replace with your timezone
india_timezone = pytz.timezone('Asia/Kolkata')
now = datetime.datetime.now(india_timezone)
now_minus_30_mins = now - datetime.timedelta(minutes=30)   

def variables(mail_addr,mail_sub,amountre,memo1,memo2,date1,date2,datef,account_id,osre=None):
    for from_addr, mail_subject, mail_body, email_datetime in zip(froms, subject, body_strings, email_time):
        if mail_addr in from_addr and mail_sub in mail_subject:       
            if email_datetime > now_minus_30_mins and email_datetime < now:
                amount = int(float(re.search(amountre, mail_body).group()))*multiple(body_strings)
                try:
                    memo = re.search(memo1, mail_body).group()
                except:
                    memo = re.search(memo2, mail_body).group()
                try:
                    date = datetime.datetime.strptime(re.search(date1, mail_body).group(), datef).strftime('%Y-%m-%d')
                except:
                    date = datetime.datetime.strptime(re.search(date2, mail_body).group(), datef).strftime('%Y-%m-%d')
                account_id = account_id
                payee_name = search_dict(payee_dict, memo)
                category_id = search_dict(category_dict, payee_name)
                if not osre == None and mail_addr == 'alerts@xyzbank.net':
                    os = int(float(re.search(osre, mail_body).group().replace(',','')))
                    memo = memo+' and Outstanding is: '+str(os)
                if not osre == None and mail_addr == 'credit_cards@xyzbank.com':
                    os = 100000 - int(float(re.search(osre, mail_body).group().replace(',','')))
                    memo = memo+' and Outstanding is: '+str(os)
                # Txn JSON
                data = {
                    "transaction": {
                        "account_id": f'{account_id}',
                        "date": date,
                        "amount": amount*1000,
                        "payee_name": payee_name,
                        "category_id": category_id if category_id != 'None' else None,
                        "memo": memo
                    }
                }
                response = requests.post(f'{endpoint}{budget_id}/transactions', headers=headers, json=data)
    return amount,memo,date,payee_name,category_id

#change all the regular exoressions according to your mail format use https://regexr.com/ for testing ur RE's or use CHAT GPT
try:
    xyz_debit = variables('your bank mail subject'
                            ,r'\d+\.\d+'
                            ,r'(?<= to )(.*?)(?= on )'
                            ,r'(?<= at )(.*?)(?= on )'
                            ,r'\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2}'
                            ,r'\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2}'
                            ,'%d-%m-%y'
                            ,'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
                            )
    print(xyz_debit)
except:
    print("Not xyz Debit")

try:
    xyz_credit = variables('your bank mail subject'
                            ,r'\d+\.\d+'
                            ,r'(?<= at )(.*?)(?= on )'
                            ,r'(?<= at )(.*?)(?= on )'
                            ,r'\b(\d{2})-(\d{2})-(\d{4})\b'
                            ,r'\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2}'
                            ,'%d-%m-%Y'
                            ,'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
                            ,r'(?<= outstanding is Rs )(.*?)(?=[.])'
                            )
    print(xyz_credit)
except:
    print("Not xyz Credit")

try:
    xyz = variables('your bank mail subject'
                        ,r'(?<= INR )\d+\.\d+'
                        ,r'(?<= Info: )(.*?)(?=[.])'
                        ,r'(?<= at )(.*?)(?= on )'
                        ,r'\b(Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s\d{1,2},\s\d{4}\b'
                        ,r'\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2}'
                        ,'%b %d, %Y'
                        ,'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
                        ,r'\d+\,\d+\.\d+'
                        )
    print(xyz)
except:
    print("Not xyz Credit")
# if __name__ == '__main__':
#     main(request, context)