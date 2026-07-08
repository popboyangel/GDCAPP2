"""
核心监控逻辑：查询 pair 地址持有的 CGC / WGDC 数量，计算比例 = CGC / WGDC。
用 symbol() 做匹配，避免 token0/token1 顺序搞反（之前已确认链上顺序与预期相反）。
"""
from eth_client import EthClient


def fetch_amounts_and_ratio(cfg):
    client = EthClient(cfg["rpc_url"])
    pair = cfg["pair_address"]
    token_a = cfg["token_a"]
    token_b = cfg["token_b"]

    dec_a = client.decimals(token_a)
    dec_b = client.decimals(token_b)

    cgc = 0.0
    wgdc = 0.0

    # 优先尝试通过 getReserves 获取
    res0, res1 = client.get_reserves(pair)
    if res0 is not None and res1 is not None:
        # 需要确定 token0 和 token1 分别对应哪个代币
        t0_addr = client.token0(pair)
        if t0_addr:
            if t0_addr.lower() == token_a.lower():
                bal_a_raw, bal_b_raw = res0, res1
            else:
                bal_a_raw, bal_b_raw = res1, res0
        else:
            # 降级：如果无法获取 token0，根据常见情况，通常地址较小的为 token0
            if token_a.lower() < token_b.lower():
                bal_a_raw, bal_b_raw = res0, res1
            else:
                bal_a_raw, bal_b_raw = res1, res0
    else:
        # 如果 getReserves 失败，回退到 balanceOf
        bal_a_raw = client.balance_of(token_a, pair)
        bal_b_raw = client.balance_of(token_b, pair)

    bal_a = bal_a_raw / (10 ** dec_a)
    bal_b = bal_b_raw / (10 ** dec_b)

    sym_a = (client.symbol(token_a) or "").upper()
    sym_b = (client.symbol(token_b) or "").upper()

    amounts = {}
    if sym_a == "CGC":
        amounts["CGC"] = bal_a
    elif sym_a == "WGDC":
        amounts["WGDC"] = bal_a

    if sym_b == "CGC":
        amounts["CGC"] = bal_b
    elif sym_b == "WGDC":
        amounts["WGDC"] = bal_b

    # 退回到已知的固定映射
    if "CGC" not in amounts or "WGDC" not in amounts:
        amounts["WGDC"] = bal_a
        amounts["CGC"] = bal_b

    cgc = amounts.get("CGC", 0.0)
    wgdc = amounts.get("WGDC", 0.0)
    
    if cgc == 0 and wgdc == 0:
        raise RuntimeError(f"获取到的余额为0。请核对 Pair 地址: {pair}")

    ratio = (cgc / wgdc) if wgdc and wgdc > 0 else 0.0
    return cgc, wgdc, ratio
