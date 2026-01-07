from db.models import get_dcas_collection, get_cases_collection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_dca_portfolio(dca_id, status=None, priority=None):
    """
    Get all cases assigned to a DCA
    """
    try:
        cases = get_cases_collection()
        
        filters = {'dca_id': dca_id}  # Use dca_id field, not assigned_dca
        
        if status:
            filters['status'] = status
        if priority:
            filters['priority'] = priority
        
        portfolio = list(cases.find(filters).sort('created_at', -1))
        
        # Convert ObjectId and datetime to string
        for case in portfolio:
            case['_id'] = str(case['_id'])
            for key in ['created_at', 'assigned_at', 'resolved_at', 'updated_at', 'sla_deadline']:
                if key in case and case[key]:
                    case[key] = case[key].isoformat()
        
        return portfolio
        
    except Exception as e:
        logger.error(f"Error getting DCA portfolio: {str(e)}")
        raise

def get_dca_performance(dca_id):
    """
    Get performance metrics for a DCA
    """
    try:
        dcas = get_dcas_collection()
        cases = get_cases_collection()
        
        dca = dcas.find_one({'dca_id': dca_id})
        if not dca:
            raise ValueError(f"DCA {dca_id} not found")
        
        # Calculate real-time metrics
        total_cases = cases.count_documents({'dca_id': dca_id})
        active_cases = cases.count_documents({
            'dca_id': dca_id,
            'status': {'$in': ['assigned', 'in_progress']}
        })
        resolved_cases = cases.count_documents({
            'dca_id': dca_id,
            'status': 'resolved'
        })
        
        # Calculate recovery metrics
        pipeline = [
            {'$match': {'dca_id': dca_id, 'status': 'resolved'}},
            {'$group': {'_id': None, 'total_recovered': {'$sum': '$amount'}}}
        ]
        recovery_result = list(cases.aggregate(pipeline))
        total_recovered = recovery_result[0]['total_recovered'] if recovery_result else 0
        
        # Calculate average recovery time
        resolved_with_time = list(cases.find({
            'dca_id': dca_id,
            'status': 'resolved',
            'resolved_at': {'$exists': True},
            'assigned_at': {'$exists': True}
        }))
        
        if resolved_with_time:
            avg_time = sum([
                (case['resolved_at'] - case['assigned_at']).days
                for case in resolved_with_time
            ]) / len(resolved_with_time)
        else:
            avg_time = 0
        
        performance = {
            'dca_id': dca_id,
            'name': dca['name'],
            'status': dca['status'],
            'performance_score': dca.get('performance_score', 0),
            'capacity': dca['capacity'],
            'current_cases': active_cases,
            'utilization': round((active_cases / dca['capacity'] * 100) if dca['capacity'] > 0 else 0, 2),
            'total_cases': total_cases,
            'active_cases': active_cases,
            'resolved_cases': resolved_cases,
            'recovery_rate': round((resolved_cases / total_cases * 100) if total_cases > 0 else 0, 2),
            'total_recovered': round(total_recovered, 2),
            'avg_recovery_time': round(avg_time, 1)
        }
        
        return performance
        
    except Exception as e:
        logger.error(f"Error getting DCA performance: {str(e)}")
        raise

def get_all_dcas(status=None):
    """
    Get list of all DCAs
    """
    try:
        dcas = get_dcas_collection()
        
        filters = {}
        if status:
            filters['status'] = status
        
        dca_list = list(dcas.find(filters).sort('name', 1))
        
        # Convert ObjectId and datetime to string
        for dca in dca_list:
            dca['_id'] = str(dca['_id'])
            for key in ['created_at', 'updated_at']:
                if key in dca and dca[key]:
                    dca[key] = dca[key].isoformat()
        
        return dca_list
        
    except Exception as e:
        logger.error(f"Error getting DCAs: {str(e)}")
        raise

def update_dca_capacity(dca_id, capacity):
    """
    Update DCA capacity
    """
    try:
        dcas = get_dcas_collection()
        
        result = dcas.update_one(
            {'dca_id': dca_id},
            {
                '$set': {
                    'capacity': capacity,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise ValueError(f"DCA {dca_id} not found")
        
        logger.info(f"DCA {dca_id} capacity updated to {capacity}")
        
        # Return updated DCA
        updated_dca = dcas.find_one({'dca_id': dca_id})
        updated_dca['_id'] = str(updated_dca['_id'])
        return updated_dca
        
    except Exception as e:
        logger.error(f"Error updating DCA capacity: {str(e)}")
        raise

def get_dca_statistics(dca_id):
    """
    Get detailed statistics for a DCA
    """
    try:
        cases = get_cases_collection()
        
        # Cases by status
        status_breakdown = {}
        for status in ['pending', 'assigned', 'in_progress', 'resolved', 'escalated']:
            count = cases.count_documents({'assigned_dca': dca_id, 'status': status})
            status_breakdown[status] = count
        
        # Cases by priority
        priority_breakdown = {}
        for priority in ['critical', 'high', 'medium', 'low']:
            count = cases.count_documents({'assigned_dca': dca_id, 'priority': priority})
            priority_breakdown[priority] = count
        
        # SLA compliance
        total_resolved = cases.count_documents({'assigned_dca': dca_id, 'status': 'resolved'})
        sla_breached = cases.count_documents({
            'assigned_dca': dca_id,
            'status': 'resolved',
            'resolved_at': {'$gt': '$sla_deadline'}
        })
        sla_compliance = round(((total_resolved - sla_breached) / total_resolved * 100) if total_resolved > 0 else 100, 2)
        
        # Amount metrics
        pipeline = [
            {'$match': {'assigned_dca': dca_id}},
            {'$group': {
                '_id': '$status',
                'total_amount': {'$sum': '$amount'},
                'count': {'$sum': 1}
            }}
        ]
        amount_breakdown = {item['_id']: item for item in cases.aggregate(pipeline)}
        
        statistics = {
            'dca_id': dca_id,
            'status_breakdown': status_breakdown,
            'priority_breakdown': priority_breakdown,
            'sla_compliance': sla_compliance,
            'amount_breakdown': amount_breakdown
        }
        
        return statistics
        
    except Exception as e:
        logger.error(f"Error getting DCA statistics: {str(e)}")
        raise

def update_dca_performance_score(dca_id):
    """
    Recalculate and update DCA performance score
    """
    try:
        dcas = get_dcas_collection()
        cases = get_cases_collection()
        
        # Get metrics
        total_cases = cases.count_documents({'assigned_dca': dca_id})
        if total_cases == 0:
            return
        
        resolved_cases = cases.count_documents({'assigned_dca': dca_id, 'status': 'resolved'})
        recovery_rate = (resolved_cases / total_cases) * 100
        
        # SLA compliance
        sla_breached = cases.count_documents({
            'assigned_dca': dca_id,
            'sla_deadline': {'$lt': datetime.utcnow()},
            'status': {'$nin': ['resolved']}
        })
        sla_compliance = ((total_cases - sla_breached) / total_cases) * 100
        
        # Calculate performance score (weighted average)
        performance_score = (recovery_rate * 0.6) + (sla_compliance * 0.4)
        
        # Update DCA
        dcas.update_one(
            {'dca_id': dca_id},
            {
                '$set': {
                    'performance_score': round(performance_score, 2),
                    'recovery_rate': round(recovery_rate, 2),
                    'total_cases': total_cases,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        logger.info(f"DCA {dca_id} performance score updated to {performance_score:.2f}")
        
    except Exception as e:
        logger.error(f"Error updating DCA performance score: {str(e)}")
        raise
