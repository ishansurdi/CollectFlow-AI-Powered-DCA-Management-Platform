from flask import Blueprint, request, jsonify
from utils.auth import token_required
from db.models import (
    get_cases_collection,
    get_accounts_collection,
    get_dcas_collection,
    get_events_collection
)
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/kpis', methods=['GET'])
@token_required
def get_kpis(current_user):
    """
    Get key performance indicators
    Role-based: FedEx sees overall, DCA sees their own
    """
    try:
        cases = get_cases_collection()
        accounts = get_accounts_collection()
        
        filters = {}
        if current_user['role'].startswith('dca'):
            filters['assigned_dca'] = current_user.get('dca_id')
        
        # Total cases
        total_cases = cases.count_documents(filters)
        
        # Active cases
        active_cases = cases.count_documents({
            **filters,
            'status': {'$in': ['assigned', 'in_progress']}
        })
        
        # Resolved cases
        resolved_cases = cases.count_documents({
            **filters,
            'status': 'resolved'
        })
        
        # Recovery rate
        recovery_rate = (resolved_cases / total_cases * 100) if total_cases > 0 else 0
        
        # Total amount in recovery
        pipeline = [
            {'$match': {**filters, 'status': {'$in': ['assigned', 'in_progress']}}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ]
        amount_result = list(cases.aggregate(pipeline))
        total_amount = amount_result[0]['total'] if amount_result else 0
        
        # SLA breaches
        sla_breaches = cases.count_documents({
            **filters,
            'sla_deadline': {'$lt': datetime.utcnow()},
            'status': {'$nin': ['resolved', 'written_off']}
        })
        
        # Cases by priority
        priority_dist = {}
        for priority in ['critical', 'high', 'medium', 'low']:
            count = cases.count_documents({**filters, 'priority': priority})
            priority_dist[priority] = count
        
        # Cases by status
        status_dist = {}
        for status in ['pending', 'assigned', 'in_progress', 'resolved', 'escalated']:
            count = cases.count_documents({**filters, 'status': status})
            status_dist[status] = count
        
        kpis = {
            'total_cases': total_cases,
            'active_cases': active_cases,
            'resolved_cases': resolved_cases,
            'recovery_rate': round(recovery_rate, 2),
            'total_amount_in_recovery': round(total_amount, 2),
            'sla_breaches': sla_breaches,
            'priority_distribution': priority_dist,
            'status_distribution': status_dist
        }
        
        return jsonify(kpis), 200
        
    except Exception as e:
        logger.error(f"Error fetching KPIs: {str(e)}")
        return jsonify({'error': 'Failed to fetch KPIs'}), 500

@dashboard_bp.route('/trends', methods=['GET'])
@token_required
def get_trends(current_user):
    """
    Get trending data for charts
    Query params: days (default 30)
    """
    try:
        days = int(request.args.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        cases = get_cases_collection()
        
        filters = {'created_at': {'$gte': start_date}}
        if current_user['role'].startswith('dca'):
            filters['assigned_dca'] = current_user.get('dca_id')
        
        # Cases created over time
        pipeline = [
            {'$match': filters},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ]
        cases_trend = list(cases.aggregate(pipeline))
        
        # Recovery trend
        recovery_filters = {**filters, 'status': 'resolved'}
        pipeline = [
            {'$match': recovery_filters},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$resolved_at'}},
                'count': {'$sum': 1},
                'amount': {'$sum': '$amount'}
            }},
            {'$sort': {'_id': 1}}
        ]
        recovery_trend = list(cases.aggregate(pipeline))
        
        trends = {
            'cases_created': cases_trend,
            'cases_resolved': recovery_trend
        }
        
        return jsonify(trends), 200
        
    except Exception as e:
        logger.error(f"Error fetching trends: {str(e)}")
        return jsonify({'error': 'Failed to fetch trends'}), 500

@dashboard_bp.route('/dca-rankings', methods=['GET'])
@token_required
def get_dca_rankings(current_user):
    """
    Get DCA performance rankings (FedEx only)
    """
    try:
        if not current_user['role'].startswith('fedex'):
            return jsonify({'error': 'Unauthorized'}), 403
        
        dcas = get_dcas_collection()
        
        # Get all active DCAs sorted by performance score
        dca_list = list(dcas.find(
            {'status': 'active'},
            {
                'dca_id': 1,
                'name': 1,
                'performance_score': 1,
                'recovery_rate': 1,
                'total_recovered': 1,
                'current_cases': 1,
                'avg_recovery_time': 1
            }
        ).sort('performance_score', -1).limit(10))
        
        # Convert ObjectId to string
        for dca in dca_list:
            dca['_id'] = str(dca['_id'])
        
        return jsonify({
            'rankings': dca_list,
            'count': len(dca_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching DCA rankings: {str(e)}")
        return jsonify({'error': 'Failed to fetch rankings'}), 500

@dashboard_bp.route('/activity-feed', methods=['GET'])
@token_required
def get_activity_feed(current_user):
    """
    Get recent activity events
    Query params: limit (default 50)
    """
    try:
        limit = int(request.args.get('limit', 50))
        events = get_events_collection()
        
        filters = {}
        if current_user['role'].startswith('dca'):
            # Get events for cases assigned to this DCA
            cases = get_cases_collection()
            dca_cases = cases.find(
                {'assigned_dca': current_user.get('dca_id')},
                {'case_id': 1}
            )
            case_ids = [case['case_id'] for case in dca_cases]
            filters['case_id'] = {'$in': case_ids}
        
        # Get recent events
        recent_events = list(events.find(
            filters,
            {
                'event_id': 1,
                'case_id': 1,
                'event_type': 1,
                'description': 1,
                'user_id': 1,
                'timestamp': 1
            }
        ).sort('timestamp', -1).limit(limit))
        
        # Convert ObjectId and datetime to string
        for event in recent_events:
            event['_id'] = str(event['_id'])
            event['timestamp'] = event['timestamp'].isoformat()
        
        return jsonify({
            'events': recent_events,
            'count': len(recent_events)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching activity feed: {str(e)}")
        return jsonify({'error': 'Failed to fetch activity feed'}), 500

@dashboard_bp.route('/alerts', methods=['GET'])
@token_required
def get_alerts(current_user):
    """
    Get system alerts (SLA breaches, escalations, etc.)
    """
    try:
        cases = get_cases_collection()
        
        filters = {}
        if current_user['role'].startswith('dca'):
            filters['assigned_dca'] = current_user.get('dca_id')
        
        alerts = []
        
        # SLA breaches
        sla_breached = list(cases.find({
            **filters,
            'sla_deadline': {'$lt': datetime.utcnow()},
            'status': {'$nin': ['resolved', 'written_off']}
        }).limit(20))
        
        for case in sla_breached:
            alerts.append({
                'type': 'sla_breach',
                'severity': 'high',
                'case_id': case['case_id'],
                'message': f"Case {case['case_id']} has breached SLA",
                'timestamp': case['sla_deadline'].isoformat()
            })
        
        # Escalated cases
        escalated = list(cases.find({
            **filters,
            'status': 'escalated'
        }).limit(10))
        
        for case in escalated:
            alerts.append({
                'type': 'escalation',
                'severity': 'medium',
                'case_id': case['case_id'],
                'message': f"Case {case['case_id']} has been escalated",
                'timestamp': case['updated_at'].isoformat()
            })
        
        # Sort by timestamp (most recent first)
        alerts.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'alerts': alerts,
            'count': len(alerts)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching alerts: {str(e)}")
        return jsonify({'error': 'Failed to fetch alerts'}), 500


@dashboard_bp.route('/business-metrics', methods=['GET'])
@token_required
def get_business_metrics(current_user):
    """
    Get comprehensive business-oriented KPIs and metrics
    """
    try:
        cases = get_cases_collection()
        accounts = get_accounts_collection()
        
        filters = {}
        if current_user['role'].startswith('dca'):
            filters['assigned_dca'] = current_user.get('dca_id')
        
        # Days Sales Outstanding (DSO)
        # Average days to collect payment
        resolved_cases = list(cases.find({**filters, 'status': 'resolved'}).limit(1000))
        if resolved_cases:
            total_days = sum([
                (c.get('resolved_at', datetime.utcnow()) - c.get('created_at', datetime.utcnow())).days
                for c in resolved_cases
            ])
            dso = round(total_days / len(resolved_cases), 1)
        else:
            dso = 0
        
        # Collection Efficiency Rate (CER)
        # (Amount Collected / Amount Assigned) * 100
        total_assigned = cases.aggregate([
            {'$match': filters},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ])
        total_assigned = list(total_assigned)
        assigned_amount = total_assigned[0]['total'] if total_assigned else 1
        
        # Use amount_recovered if available, otherwise use amount for resolved cases
        # This handles cases where amount_recovered field may not be populated
        total_recovered = cases.aggregate([
            {'$match': {**filters, 'status': 'resolved'}},
            {'$project': {
                'recovered': {'$ifNull': ['$amount_recovered', '$amount']}
            }},
            {'$group': {'_id': None, 'total': {'$sum': '$recovered'}}}
        ])
        total_recovered = list(total_recovered)
        recovered_amount = total_recovered[0]['total'] if total_recovered else 0
        
        collection_efficiency = round((recovered_amount / assigned_amount * 100), 2) if assigned_amount > 0 else 0
        
        # Recovery Yield
        # Average amount recovered per case
        resolved_count = cases.count_documents({**filters, 'status': 'resolved'})
        recovery_yield = round(recovered_amount / resolved_count, 2) if resolved_count > 0 else 0
        
        # Right Party Contact Rate (RPC)
        # Percentage of successful contact attempts (mock calculation)
        total_cases_count = cases.count_documents(filters)
        rpc_rate = round(65.5, 2)  # Mock: 65.5% contact success rate
        
        # Promise to Pay (PTP) Kept Rate (mock calculation)
        ptp_kept_rate = round(78.3, 2)  # Mock: 78.3% PTP kept rate
        
        # Net Recovery Rate (NRR)
        # (Amount Recovered - DCA Fees) / Amount Assigned
        dca_fees = recovered_amount * 0.25  # Assume 25% commission
        net_recovered = recovered_amount - dca_fees
        net_recovery_rate = round((net_recovered / assigned_amount * 100), 2) if assigned_amount > 0 else 0
        
        # Roll Rate (accounts moving to next aging bucket) - mock
        roll_rate = round(12.8, 2)  # Mock: 12.8% roll rate
        
        # Liquidation Rate (cases resolved / total cases)
        total_cases = cases.count_documents(filters)
        resolved_total = cases.count_documents({**filters, 'status': 'resolved'})
        liquidation_rate = round((resolved_total / total_cases * 100), 2) if total_cases > 0 else 0
        
        # Average Time to First Payment (TTFP) - mock
        avg_ttfp = round(18.5, 1)  # Mock: 18.5 days
        
        # Cost to Collect
        # Cost per dollar recovered (operational cost / amount recovered)
        operational_cost = recovered_amount * 0.15  # Assume 15% operational cost
        cost_to_collect = round((operational_cost / recovered_amount), 2) if recovered_amount > 0 else 0
        
        # SLA Compliance Rate
        # Percentage of completed cases that met their SLA deadline
        total_completed = cases.count_documents({**filters, 'status': {'$in': ['resolved', 'written_off']}})
        
        # Count completed cases that were resolved AFTER their SLA deadline
        sla_breached_completed = cases.count_documents({
            **filters,
            'status': {'$in': ['resolved', 'written_off']},
            '$expr': {'$gt': ['$resolved_at', '$sla_deadline']}
        })
        
        # SLA compliance = cases completed on time / total completed
        sla_compliance = round(((total_completed - sla_breached_completed) / total_completed * 100), 2) if total_completed > 0 else 100
        
        # Trend data (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        daily_recovery = []
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            next_date = date + timedelta(days=1)
            
            day_recovered = cases.aggregate([
                {'$match': {
                    **filters,
                    'resolved_at': {'$gte': date, '$lt': next_date}
                }},
                {'$project': {
                    'recovered': {'$ifNull': ['$amount_recovered', '$amount']}
                }},
                {'$group': {'_id': None, 'total': {'$sum': '$recovered'}}}
            ])
            day_recovered = list(day_recovered)
            amount = day_recovered[0]['total'] if day_recovered else 0
            
            daily_recovery.append({
                'date': date.strftime('%Y-%m-%d'),
                'amount': round(amount, 2)
            })
        
        metrics = {
            'dso': dso,
            'collection_efficiency_rate': collection_efficiency,
            'recovery_yield': recovery_yield,
            'rpc_rate': rpc_rate,
            'ptp_kept_rate': ptp_kept_rate,
            'net_recovery_rate': net_recovery_rate,
            'roll_rate': roll_rate,
            'liquidation_rate': liquidation_rate,
            'avg_time_to_first_payment': avg_ttfp,
            'cost_to_collect': cost_to_collect,
            'sla_compliance_rate': sla_compliance,
            'total_assigned_amount': round(assigned_amount, 2),
            'total_recovered_amount': round(recovered_amount, 2),
            'net_recovered_amount': round(net_recovered, 2),
            'dca_commission': round(dca_fees, 2),
            'operational_cost': round(operational_cost, 2),
            'daily_recovery_trend': daily_recovery
        }
        
        return jsonify(metrics), 200
        
    except Exception as e:
        logger.error(f"Error getting business metrics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dashboard_bp.route('/portfolio-analytics', methods=['GET'])
@token_required
def get_portfolio_analytics(current_user):
    """
    Get portfolio segmentation and analytics
    """
    try:
        cases = get_cases_collection()
        accounts = get_accounts_collection()
        
        filters = {}
        if current_user['role'].startswith('dca'):
            filters['assigned_dca'] = current_user.get('dca_id')
        
        # Portfolio by aging bucket
        aging_buckets = [
            {'name': '0-30 days', 'min': 0, 'max': 30},
            {'name': '31-60 days', 'min': 31, 'max': 60},
            {'name': '61-90 days', 'min': 61, 'max': 90},
            {'name': '91-180 days', 'min': 91, 'max': 180},
            {'name': '180+ days', 'min': 181, 'max': 99999}
        ]
        
        aging_distribution = []
        for bucket in aging_buckets:
            count = accounts.count_documents({
                'overdue_days': {'$gte': bucket['min'], '$lt': bucket['max']}
            })
            
            amount = accounts.aggregate([
                {'$match': {
                    'overdue_days': {'$gte': bucket['min'], '$lt': bucket['max']}
                }},
                {'$group': {'_id': None, 'total': {'$sum': '$amount_overdue'}}}
            ])
            amount = list(amount)
            total_amount = amount[0]['total'] if amount else 0
            
            aging_distribution.append({
                'bucket': bucket['name'],
                'count': count,
                'amount': round(total_amount, 2)
            })
        
        # Portfolio by amount range
        amount_ranges = [
            {'name': '$0 - $1K', 'min': 0, 'max': 1000},
            {'name': '$1K - $5K', 'min': 1000, 'max': 5000},
            {'name': '$5K - $10K', 'min': 5000, 'max': 10000},
            {'name': '$10K - $50K', 'min': 10000, 'max': 50000},
            {'name': '$50K+', 'min': 50000, 'max': 999999999}
        ]
        
        amount_distribution = []
        for range_item in amount_ranges:
            count = cases.count_documents({
                **filters,
                'amount': {'$gte': range_item['min'], '$lt': range_item['max']}
            })
            
            amount_distribution.append({
                'range': range_item['name'],
                'count': count
            })
        
        # Top 10 accounts by amount
        top_accounts = list(accounts.find().sort('amount_overdue', -1).limit(10))
        top_accounts_list = [{
            'account_number': acc['account_number'],
            'customer_name': acc.get('customer_name', 'N/A'),
            'amount': round(acc['amount_overdue'], 2),
            'overdue_days': acc['overdue_days']
        } for acc in top_accounts]
        
        analytics = {
            'aging_distribution': aging_distribution,
            'amount_distribution': amount_distribution,
            'top_accounts': top_accounts_list
        }
        
        return jsonify(analytics), 200
        
    except Exception as e:
        logger.error(f"Error getting portfolio analytics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
