"""Base L2 USDC Payment Monitor — GARCAR Enterprise"""
import os, json

BASE_RPC = os.environ.get('BASE_RPC_URL', 'https://mainnet.base.org')
WALLET = os.environ.get('WALLET_ADDRESS', '')

# USDC contract on Base mainnet
USDC_BASE = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'

def check_usdc_balance_rpc(wallet: str) -> float:
    """Check USDC balance via raw RPC — no web3 dependency"""
    import requests
    # balanceOf(address) = keccak256 first 4 bytes = 0x70a08231
    padded = wallet.lower().replace('0x', '').zfill(64)
    data = '0x70a08231' + padded
    payload = {
        'jsonrpc': '2.0', 'method': 'eth_call',
        'params': [{'to': USDC_BASE, 'data': data}, 'latest'],
        'id': 1
    }
    r = requests.post(BASE_RPC, json=payload, timeout=10)
    result = r.json().get('result', '0x0')
    balance = int(result, 16) / 1e6  # USDC has 6 decimals
    return balance

def get_latest_block() -> int:
    import requests
    payload = {'jsonrpc': '2.0', 'method': 'eth_blockNumber', 'params': [], 'id': 1}
    r = requests.post(BASE_RPC, json=payload, timeout=10)
    return int(r.json().get('result', '0x0'), 16)

def report():
    if not WALLET:
        print('Set WALLET_ADDRESS env var')
        return
    try:
        balance = check_usdc_balance_rpc(WALLET)
        block = get_latest_block()
        print(f'Base USDC Balance: ${balance:,.2f}')
        print(f'Latest Block: {block:,}')
        print(f'RPC: {BASE_RPC}')
        return {'balance_usdc': balance, 'block': block}
    except Exception as e:
        print(f'Base RPC error: {e}')
        return {'error': str(e)}

if __name__ == '__main__':
    report()
