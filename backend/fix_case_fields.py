#!/usr/bin/env python3
"""Fix case field names - change assigned_to to assigned_dca"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from db.mongo import get_db

def fix_field_names():
    db = get_db()
    
    # Get all cases with assigned_to field
    cases_to_fix = list(db.cases.find({'assigned_to': {'$exists': True}}))
    
    print(f"Found {len(cases_to_fix)} cases with 'assigned_to' field")
    
    fixed = 0
    for case in cases_to_fix:
        if case.get('assigned_to') and case['assigned_to'] != 'Unassigned':
            # Rename field from assigned_to to assigned_dca
            db.cases.update_one(
                {'_id': case['_id']},
                {
                    '$set': {'assigned_dca': case['assigned_to']},
                    '$unset': {'assigned_to': ''}
                }
            )
            fixed += 1
            print(f"Fixed {case['case_id']}: assigned_dca = {case['assigned_to']}")
    
    print(f"\n✓ Fixed {fixed} cases!")
    
    # Verify
    print("\nVerification - Cases by DCA:")
    dcas = list(db.dcas.find())
    for dca in dcas:
        count = db.cases.count_documents({'assigned_dca': dca['dca_id']})
        print(f"  {dca['dca_id']} ({dca['name']}): {count} cases")

if __name__ == '__main__':
    fix_field_names()
