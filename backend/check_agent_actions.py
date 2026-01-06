#!/usr/bin/env python3
"""Check what actions autonomous agents have taken"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from db.mongo import get_db
from datetime import datetime, timedelta

def check_agent_actions():
    db = get_db()
    
    print("=" * 80)
    print("AUTONOMOUS AGENT ACTIVITY REPORT")
    print("=" * 80)
    
    # Check recent cases
    print("\n1. RECENT CASES (Last 10):")
    print("-" * 80)
    cases = list(db.cases.find().sort('created_at', -1).limit(10))
    for case in cases:
        print(f"\nCase ID: {case['case_id']}")
        print(f"  Status: {case.get('status', 'N/A')}")
        print(f"  Priority: {case.get('priority', 'N/A')}")
        print(f"  Assigned to: {case.get('assigned_to', 'Unassigned')}")
        print(f"  Created: {case.get('created_at', 'N/A')}")
        if case.get('metadata', {}).get('auto_created'):
            print(f"  🤖 AUTO-CREATED BY AGENT")
    
    # Check autonomous events
    print("\n\n2. AUTONOMOUS AGENT EVENTS:")
    print("-" * 80)
    events = list(db.events.find({'metadata.autonomous': True}).sort('timestamp', -1).limit(20))
    if events:
        for event in events:
            timestamp = event['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[{timestamp}] {event['event_type']}")
            print(f"  Description: {event['description']}")
            print(f"  Case: {event.get('case_id', 'N/A')}")
            if event.get('metadata'):
                agent = event['metadata'].get('agent_name', 'Unknown')
                confidence = event['metadata'].get('confidence', 'N/A')
                print(f"  Agent: {agent} (Confidence: {confidence})")
    else:
        print("No autonomous events found yet.")
    
    # Check case assignments by agents
    print("\n\n3. CASES ASSIGNED BY AGENTS:")
    print("-" * 80)
    assigned_cases = list(db.cases.find({'metadata.assigned_by_agent': True}))
    if assigned_cases:
        for case in assigned_cases:
            print(f"\n{case['case_id']} → {case.get('assigned_to', 'Unassigned')}")
            print(f"  Priority: {case.get('priority', 'N/A')}")
            print(f"  Amount: ${case.get('debt_amount', 0):,.2f}")
    else:
        print("No cases assigned by agents yet.")
    
    # Check escalations
    print("\n\n4. AGENT ESCALATIONS:")
    print("-" * 80)
    escalations = list(db.events.find({
        'event_type': 'case_escalated',
        'metadata.autonomous': True
    }).sort('timestamp', -1).limit(10))
    if escalations:
        for esc in escalations:
            timestamp = esc['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[{timestamp}] {esc['case_id']}")
            print(f"  Reason: {esc.get('description', 'N/A')}")
    else:
        print("No escalations by agents yet.")
    
    # Statistics
    print("\n\n5. OVERALL STATISTICS:")
    print("-" * 80)
    total_events = db.events.count_documents({'metadata.autonomous': True})
    total_cases = db.cases.count_documents({})
    auto_created = db.cases.count_documents({'metadata.auto_created': True})
    auto_assigned = db.cases.count_documents({'metadata.assigned_by_agent': True})
    
    print(f"Total Cases: {total_cases}")
    print(f"Auto-created by Agents: {auto_created}")
    print(f"Auto-assigned by Agents: {auto_assigned}")
    print(f"Total Autonomous Events: {total_events}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_agent_actions()
