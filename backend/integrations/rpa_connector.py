"""
RPA Connector - Integration layer for legacy systems (SAP, Oracle, etc.)
Demonstrates how external ERP systems can integrate with DCA Management System
"""

import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class RPAConnector:
    """
    Base RPA connector for legacy system integration
    Supports bidirectional data flow between DCA system and enterprise ERPs
    """
    
    def __init__(self, system_name: str, base_url: str = None, api_key: str = None):
        self.system_name = system_name
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        
        logger.info(f"RPA Connector initialized for {system_name}")
    
    def push_overdue_accounts(self, accounts: List[Dict]) -> Dict:
        """
        Push overdue accounts from legacy ERP to DCA system
        Used by RPA bots to automatically sync accounts
        """
        try:
            success_count = 0
            failed_accounts = []
            
            for account in accounts:
                try:
                    # Transform legacy data format to DCA system format
                    dca_account = self._transform_account_data(account)
                    
                    # Call DCA API to create/update account
                    response = self._call_dca_api('/api/accounts/sync', dca_account)
                    
                    if response.get('success'):
                        success_count += 1
                        logger.info(f"Synced account {account.get('account_id')}")
                    else:
                        failed_accounts.append(account.get('account_id'))
                        
                except Exception as e:
                    logger.error(f"Failed to sync account {account.get('account_id')}: {str(e)}")
                    failed_accounts.append(account.get('account_id'))
            
            return {
                'status': 'completed',
                'total_accounts': len(accounts),
                'success_count': success_count,
                'failed_count': len(failed_accounts),
                'failed_accounts': failed_accounts,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error pushing accounts: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def pull_case_updates(self, case_ids: List[str] = None) -> List[Dict]:
        """
        Pull case updates from DCA system back to legacy ERP
        Used by RPA bots for status synchronization
        """
        try:
            # Call DCA API to get case updates
            endpoint = '/api/cases/export'
            params = {'case_ids': case_ids} if case_ids else {}
            
            cases = self._call_dca_api(endpoint, params, method='GET')
            
            # Transform to legacy system format
            legacy_updates = []
            for case in cases:
                legacy_update = self._transform_to_legacy_format(case)
                legacy_updates.append(legacy_update)
            
            logger.info(f"Pulled {len(legacy_updates)} case updates")
            return legacy_updates
            
        except Exception as e:
            logger.error(f"Error pulling case updates: {str(e)}")
            return []
    
    def sync_payment_received(self, payment_data: Dict) -> Dict:
        """
        Sync payment information from DCA system to legacy ERP
        Real-time financial reconciliation
        """
        try:
            # Transform payment data to legacy format
            legacy_payment = {
                'transaction_id': payment_data.get('payment_id'),
                'account_number': payment_data.get('account_number'),
                'amount': payment_data.get('amount'),
                'payment_date': payment_data.get('payment_date'),
                'payment_method': payment_data.get('method'),
                'dca_reference': payment_data.get('case_id'),
                'status': 'posted'
            }
            
            # Call legacy system API (mock)
            response = self._post_to_legacy_system('/api/payments', legacy_payment)
            
            return {
                'status': 'success',
                'transaction_id': legacy_payment['transaction_id'],
                'legacy_reference': response.get('reference_number'),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error syncing payment: {str(e)}")
            return {'status': 'error', 'message': str(e)}
    
    def _transform_account_data(self, legacy_account: Dict) -> Dict:
        """Transform legacy ERP account format to DCA system format"""
        return {
            'account_number': legacy_account.get('account_id', legacy_account.get('account_number')),
            'customer_id': legacy_account.get('customer_id'),
            'customer_name': legacy_account.get('customer_name'),
            'amount_overdue': float(legacy_account.get('outstanding_balance', 0)),
            'original_amount': float(legacy_account.get('original_invoice_amount', 0)),
            'overdue_days': int(legacy_account.get('days_overdue', 0)),
            'invoice_date': legacy_account.get('invoice_date'),
            'due_date': legacy_account.get('due_date'),
            'currency': legacy_account.get('currency', 'USD'),
            'business_unit': legacy_account.get('business_unit'),
            'contact_phone': legacy_account.get('phone'),
            'contact_email': legacy_account.get('email'),
            'external_reference': legacy_account.get('erp_reference'),
            'synced_from': self.system_name,
            'sync_timestamp': datetime.utcnow().isoformat()
        }
    
    def _transform_to_legacy_format(self, dca_case: Dict) -> Dict:
        """Transform DCA case format to legacy ERP format"""
        return {
            'erp_reference': dca_case.get('external_reference'),
            'dca_case_id': dca_case.get('case_id'),
            'account_number': dca_case.get('account_number'),
            'collection_status': self._map_status_to_legacy(dca_case.get('status')),
            'assigned_agency': dca_case.get('assigned_dca'),
            'amount_recovered': dca_case.get('amount_recovered', 0),
            'last_contact_date': dca_case.get('last_contact_date'),
            'next_action_date': dca_case.get('next_action_date'),
            'resolution_date': dca_case.get('resolved_at'),
            'notes': dca_case.get('latest_note'),
            'sync_timestamp': datetime.utcnow().isoformat()
        }
    
    def _map_status_to_legacy(self, dca_status: str) -> str:
        """Map DCA status codes to legacy system status codes"""
        status_mapping = {
            'pending': 'PENDING_ASSIGNMENT',
            'assigned': 'WITH_AGENCY',
            'in_progress': 'IN_COLLECTION',
            'resolved': 'CLOSED_COLLECTED',
            'written_off': 'CLOSED_UNCOLLECTIBLE',
            'escalated': 'ESCALATED'
        }
        return status_mapping.get(dca_status, 'UNKNOWN')
    
    def _call_dca_api(self, endpoint: str, data: Dict, method: str = 'POST') -> Dict:
        """Call DCA Management System API"""
        # Mock implementation - in production, this would call actual DCA API
        logger.info(f"Calling DCA API: {method} {endpoint}")
        return {'success': True, 'data': data}
    
    def _post_to_legacy_system(self, endpoint: str, data: Dict) -> Dict:
        """Post data to legacy ERP system"""
        # Mock implementation - in production, this would call legacy system
        logger.info(f"Posting to {self.system_name}: {endpoint}")
        return {'status': 'success', 'reference_number': f"REF-{uuid.uuid4().hex[:8].upper()}"}
    
    def health_check(self) -> Dict:
        """Check connectivity to legacy system"""
        try:
            # Mock health check
            return {
                'system': self.system_name,
                'status': 'connected',
                'last_sync': datetime.utcnow().isoformat(),
                'api_version': '1.0.0'
            }
        except Exception as e:
            return {
                'system': self.system_name,
                'status': 'error',
                'message': str(e)
            }


class SAPConnector(RPAConnector):
    """
    SAP-specific RPA connector
    Handles SAP FI/CO module integration for AR aging reports
    """
    
    def __init__(self, sap_server: str = None, client: str = None):
        super().__init__('SAP_ERP', sap_server)
        self.client = client
        logger.info(f"SAP Connector initialized for client {client}")
    
    def extract_ar_aging(self, business_unit: str = None, cutoff_days: int = 7) -> List[Dict]:
        """
        Extract AR Aging report from SAP
        Simulates SAP RFC call to fetch overdue accounts
        """
        logger.info(f"Extracting SAP AR Aging for business unit: {business_unit}, cutoff: {cutoff_days} days")
        
        # Mock SAP data extraction
        # In production, this would use SAP RFC/BAPI calls
        mock_sap_accounts = [
            {
                'account_id': 'SAP-' + str(1000000 + i),
                'customer_id': f'CUST-{i:04d}',
                'customer_name': f'SAP Customer {i}',
                'outstanding_balance': 5000 + (i * 100),
                'original_invoice_amount': 6000 + (i * 100),
                'days_overdue': cutoff_days + i,
                'invoice_date': '2025-11-15',
                'due_date': '2025-12-15',
                'currency': 'USD',
                'business_unit': business_unit or 'BU-001',
                'erp_reference': f'SAP-INV-{i:06d}'
            }
            for i in range(3)
        ]
        
        return mock_sap_accounts


class OracleConnector(RPAConnector):
    """
    Oracle EBS-specific RPA connector
    Handles Oracle Financials AR integration
    """
    
    def __init__(self, oracle_db: str = None):
        super().__init__('ORACLE_EBS', oracle_db)
        logger.info("Oracle Connector initialized")
    
    def extract_receivables(self, aging_bucket: str = '30+') -> List[Dict]:
        """
        Extract receivables from Oracle AR
        Simulates Oracle SQL query execution
        """
        logger.info(f"Extracting Oracle receivables for aging bucket: {aging_bucket}")
        
        # Mock Oracle data extraction
        mock_oracle_accounts = [
            {
                'account_number': f'ORA-{100000 + i}',
                'customer_id': f'ORACUST-{i:04d}',
                'customer_name': f'Oracle Customer {i}',
                'outstanding_balance': 8000 + (i * 150),
                'original_invoice_amount': 9000 + (i * 150),
                'days_overdue': 30 + i,
                'invoice_date': '2025-11-01',
                'due_date': '2025-12-01',
                'currency': 'USD',
                'business_unit': 'LOGISTICS',
                'erp_reference': f'ORA-TRX-{i:06d}'
            }
            for i in range(3)
        ]
        
        return mock_oracle_accounts


# Factory function for creating RPA connectors
def create_rpa_connector(system_type: str, **kwargs) -> RPAConnector:
    """
    Factory function to create appropriate RPA connector
    
    Args:
        system_type: 'SAP', 'ORACLE', or 'GENERIC'
        **kwargs: System-specific configuration
    
    Returns:
        Appropriate RPAConnector instance
    """
    connectors = {
        'SAP': SAPConnector,
        'ORACLE': OracleConnector,
        'GENERIC': RPAConnector
    }
    
    connector_class = connectors.get(system_type.upper(), RPAConnector)
    return connector_class(**kwargs)
