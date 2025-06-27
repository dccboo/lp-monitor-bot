from pysui import SuiClient  # 修改导入语句

class SuiHandler:
    def __init__(self, config):
        self.client = SuiClient(config['rpc_url'])
        
    def get_lp_status(self, contract_address, monitor_address):
        try:
            # 示例查询（需要根据实际合约调整）
            objects = self.client.get_objects(monitor_address)
            has_lp = any('liquidity' in obj['type'] for obj in objects)
            
            return {
                'active': has_lp,
                'action': None
            }
        except Exception as e:
            logger.error(f"Sui error: {e}")
            return {'error': str(e)}
