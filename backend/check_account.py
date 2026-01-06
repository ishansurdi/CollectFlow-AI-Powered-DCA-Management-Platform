from db.models import get_accounts_collection
import json

accounts = get_accounts_collection()
acc = accounts.find_one({'account_number': 'ACC004'})

print(json.dumps({
    'account_number': acc['account_number'],
    'amount_overdue': acc.get('amount_overdue'),
    'overdue_days': acc.get('overdue_days'),
    'original_amount': acc.get('original_amount'),
    'customer_id': acc.get('customer_id')
}, indent=2))
