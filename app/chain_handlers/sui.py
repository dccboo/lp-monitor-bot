import requests
import logging

logger = logging.getLogger(__name__)

class SuiHandler:
    def __init__(self, config):
        self.rpc_url = config['rpc_url']
        
    def get_lp_status(self, contract_address, monitor_address):
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "suix_getBalance",
                "params": [monitor_address],
                "id": 1
            }
            response = requests.post(self.rpc_url, json=payload).json()
            balance = response.get('result', {}).get('totalBalance', 0)
            
            return {
                'active': balance > 0,
                'balance': str(balance),
                'action': None
            }
        except Exception as e:
            logger.error(f"Sui error: {e}")
            return {'error': str(e)}
