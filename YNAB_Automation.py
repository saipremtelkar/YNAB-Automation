def main(request, context):
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

    new=[]
    msgs = []
    body=[]
    subject=[]
    froms=[]
    email_time=[]
    body_strings = []

    # Connection with GMAIL using SSL
    my_mail = imaplib.IMAP4_SSL('imap.gmail.com')
    my_mail.login("yourmail@mail.com", "password")
    my_mail.select('"inbox"')
    response = my_mail.search(None, 'ALL')[1][0].split()

    for num in response:
        typ, data = my_mail.fetch(num, '(RFC822)')
        new.append(data)

    for msg in new[::-1]:
        for response_part in msg:
            if type(response_part) is tuple:
                my_msg=email.message_from_bytes((response_part[1]))


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
        ['credit_cards@bank2bank.com', 'alerts@yourbank.net'])


    for num in mail_id_list:
        typ, data = my_mail.fetch(num, '(RFC822)')
        msgs.append(data)

    for msg in msgs[::-1]:
        for response_part in msg:
            if type(response_part) is tuple:
                my_msg=email.message_from_bytes((response_part[1]))
                subject.append(my_msg['subject'])
                froms.append(my_msg['from'])
                time_string = re.search(r'(.*\+\d{4})', my_msg.get("Date")).group(1)
                email_datetime = datetime.datetime.strptime(time_string, '%a, %d %b %Y %H:%M:%S %z').astimezone(pytz.timezone('Asia/Kolkata'))
                email_time.append(email_datetime)
                if my_msg.is_multipart():
                    for part in my_msg.get_payload():
                        body.append(part.get_payload(decode=True).decode('utf-8'))
                else:
                    body.append(my_msg.get_payload(decode=True).decode('utf-8'))

    for i in body:
        soup = BeautifulSoup(i, 'html.parser')
        res = soup.find('body').text
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

    india_timezone = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(india_timezone)
    now_minus_30_mins = now - datetime.timedelta(minutes=30)   

    def variables(mail_addr,mail_sub,amountres,memores,dateres,datef,account_id,osres):
        for from_addr, mail_subject, mail_body, email_datetime in zip(froms, subject, body_strings, email_time):
            if mail_addr in from_addr and mail_sub in mail_subject:   
                if email_datetime > now_minus_30_mins and email_datetime < now:
                    amount=[]
                    memo=[]
                    date=[]
                    os=None
                    
                    for amountre in amountres:
                        match = re.search(amountre, mail_body)
                        if match:
                            amount = int(float((re.search(amountre, mail_body).group()).replace(",", "")))*multiple(mail_body)
                            break
                    for memore in memores:
                        match = re.search(memore, mail_body)
                        if match:
                            if re.search(memore, mail_body).group() == 'from bank2 Bank.':
                                memo = re.findall(memore, mail_body)[1]
                            else:
                                memo = re.search(memore, mail_body).group()
                            break
                        else:
                            memo = None
                    for datere in dateres:
                        match = re.search(datere, mail_body)
                        if match:
                            try:
                                date = datetime.datetime.strptime(re.search(datere, mail_body).group(), datef).strftime('%Y-%m-%d')
                            except ValueError:
                                date = datetime.datetime.strptime(re.search(datere, mail_body).group(), '%d-%m-%Y').strftime('%Y-%m-%d')
                        else:
                            date = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d')
                        break
                    account_id = account_id
                    payee_name = search_dict(payee_dict, memo)
                    category_id = search_dict(category_dict, payee_name)
                    for osre in osres:
                        match = re.search(osre, mail_body)
                        if match:
                            if mail_addr == 'alerts@yourbank.net' and mail_sub == 'Alert :  Update on your bank Bank Credit Card':
                                os = int(float((re.search(osre, mail_body).group().replace(',',''))))
                                memo = memo+' and Outstanding is: '+str(os)
                            elif mail_addr == 'alerts@yourbank.net' and mail_sub == 'View: Account update for your bank Bank A/c' and 'withdrawal' in mail_body:
                                os = int(float(re.findall(r'\d+\.\d+', mail_body)[1]))
                                memo = memo+' and Outstanding is: '+str(os)
                            if mail_addr == 'credit_cards@bank2bank.com':
                                os = 100000 - int(float(re.search(osre, mail_body).group().replace(',','')))
                                memo = memo+' and Outstanding is: '+str(os)
                        else:
                            break
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

    bank_debit = variables('alerts@yourbank.net','View: Account update for your bank Bank A/c'
                            ,[r'(?<= Rs )(.*?)(?= in )',r'(?<= Rs. )(.*?)(?= has )',r'\d+\.\d+']
                            ,[r'(?<= account of )(.*?)(?= using)',r'(?<= to )(.*?)(?= on )',r'(?<= at )(.*?)(?= on )']
                            ,[r'\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2}']
                            ,'%d-%m-%y'
                            ,'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx''
                            ,[r'\d+\.\d+']
                            )

    bank_credit = variables('alerts@yourbank.net','Alert :  Update on your bank Bank Credit Card'
                            ,[r'\d+\.\d+']
                            ,[r'(?<= at )(.*?)(?= on )']
                            ,[r'\b(\d{2})-(\d{2})-(\d{4})\b',r'\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2}']
                            ,'%d-%m-%Y'
                            ,'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx''
                            ,[r'(?<= outstanding is Rs )(.*?)(?=[.])']
                            )
    bank2 = variables('credit_cards@bank2bank.com','Transaction alert for your bank2 Bank Credit Card'
                        ,[r'(?<= INR )\d+\.\d+',r'(?<= INR )(.*?)(?= on )']
                        ,[r'(?<= Info: )(.*?)(?=[.])',r'(?<= at )(.*?)(?= on )',r'from (.+?)\.']
                        ,[r'\b(Jan(uary)?|Feb(ruary)?|Mar(ch)?|Apr(il)?|May|Jun(e)?|Jul(y)?|Aug(ust)?|Sep(tember)?|Oct(ober)?|Nov(ember)?|Dec(ember)?)\s\d{1,2},\s\d{4}\b'
                        ,r'\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2}'
                        ]
                        ,'%b %d, %Y'
                        ,'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx''
                        ,[r'\d+\,\d+\.\d+']
                    )
if __name__ == '__main__':
    main(request, context)