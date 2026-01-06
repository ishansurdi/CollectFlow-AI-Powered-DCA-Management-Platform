#!/usr/bin/env python3
"""Manually assign unassigned cases to DCAs"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from db.mongo import get_db
from datetime import datetime
import random

def assign_cases():
    db = get_db()
    
    # Get active DCAs
    dcas = list(db.dcas.find({'status': 'active'}))
    if not dcas:
        print("No active DCAs found!")
        return
    
    print(f"Found {len(dcas)} active DCAs:")
    for dca in dcas:
        print(f"  - {dca['name']} (ID: {dca['dca_id']})")
    
    # Get unassigned cases
    unassigned_cases = list(db.cases.find({
        '$or': [
            {'assigned_to': {'$exists': False}},
            {'assigned_to': None},
            {'assigned_to': 'Unassigned'}
        ],
        'status': {'$in': ['new', 'assigned']}
    }))
    
    print(f"\nFound {len(unassigned_cases)} unassigned cases")
    
    if not unassigned_cases:
        print("No cases to assign!")
        return
    
    # Assign cases round-robin
    assigned_count = 0
    for i, case in enumerate(unassigned_cases):
        dca = dcas[i % len(dcas)]
        
        # Update case
        db.cases.update_one(
            {'_id': case['_id']},
            {
                '$set': {
                    'assigned_to': dca['dca_id'],
                    'status': 'assigned',
                    'updated_at': datetime.utcnow(),
                    'metadata.assigned_by_agent': True,
                    'metadata.assignment_method': 'manual_script'
                }
            }
        )
        
        # Create event
        db.events.insert_one({
            'case_id': case['case_id'],
            'event_type': 'case_assigned',
            'description': f"Case assigned to {dca['name']}",
            'timestamp': datetime.utcnow(),
            'metadata': {
                'assigned_to': dca['dca_id'],
                'dca_name': dca['name'],
                'autonomous': False,
                'manual_assignment': True
            }
        })
        
        assigned_count += 1
        print(f"Assigned {case['case_id']} to {dca['name']}")
    
    print(f"\n✓ Successfully assigned {assigned_count} cases!")
    
    # Show summary
    print("\nDCA Portfolio Summary:")
    for dca in dcas:
        count = db.cases.count_documents({'assigned_to': dca['dca_id']})
        print(f"  {dca['name']}: {count} cases")

if __name__ == '__main__':
    assign_cases()
