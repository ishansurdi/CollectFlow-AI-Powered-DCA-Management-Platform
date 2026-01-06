#!/usr/bin/env python3
"""Check DCA user to DCA mappings"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from db.mongo import get_db

def check_mappings():
    db = get_db()
    
    print("=" * 80)
    print("DCA USER MAPPINGS")
    print("=" * 80)
    
    # Get DCA users
    users = list(db.users.find({'role': {'$regex': 'dca'}}))
    print(f"\nDCA Users ({len(users)}):")
    for u in users:
        print(f"  Email: {u['email']:30} | User_ID: {u['user_id']:15} | DCA_ID: {u.get('dca_id', 'MISSING!')}")
    
    # Get DCAs
    dcas = list(db.dcas.find())
    print(f"\nDCA Organizations ({len(dcas)}):")
    for d in dcas:
        print(f"  Name: {d['name']:35} | DCA_ID: {d['dca_id']}")
    
    # Get assigned cases
    print(f"\nCase Assignments:")
    for d in dcas:
        count = db.cases.count_documents({'assigned_to': d['dca_id']})
        print(f"  {d['dca_id']}: {count} cases")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_mappings()
