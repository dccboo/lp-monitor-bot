from aptos_sdk.async_client import RestClient
import logging

logger = logging.getLogger(__name__)

class AptosHandler:
    def __init__(self, config):
        self.client = RestClient(config['rpc_url'])
        
    def get_lp_status(self, contract_address, monitor_address):
        try:
            # 示例查询（需要根据实际合约调整）
            resource = self.client.account_resource(
                contract_address,
                "0x1::coin::CoinStore<0x1::aptos_coin::AptosCoin>"
            )
            balance = int(resource['data']['coin']['value'])
            
            return {
                'active': balance > 0,
                'balance': str(balance),
                'action': None
            }
        except Exception as e:
            logger.error(f"Aptos error: {e}")
            return {'error': str(e)}
