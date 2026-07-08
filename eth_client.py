"""
轻量以太坊 JSON-RPC 客户端，只依赖 requests，不依赖 web3.py。
用于查询 GoodChain 上代币的 balanceOf / decimals / symbol。
"""
import requests


class EthClient:
    def __init__(self, rpc_url, timeout=15):
        self.rpc_url = rpc_url
        self.timeout = timeout
        self._id = 0

    def _rpc(self, method, params):
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            resp = requests.post(self.rpc_url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"RPC error: {data['error']}")
            return data["result"]
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"网络请求失败: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"RPC 调用异常: {str(e)}")

    def eth_call(self, to, data):
        result = self._rpc("eth_call", [{"to": to, "data": data}, "latest"])
        if not result or result == "0x":
            # 可能是节点同步问题或地址错误，尝试抛出更有意义的错误
            raise RuntimeError(f"合约调用返回空结果。请检查地址 {to} 是否正确，或者 RPC 节点是否同步。")
        if len(result) < 66 and "0x" in result:
             # 如果返回的数据太短（比如只有 0x00...00），也可能是异常
             pass
        return result

    @staticmethod
    def _pad_address(addr):
        return addr.lower().replace("0x", "").rjust(64, "0")

    def balance_of(self, token_address, holder_address):
        """返回代币原始最小单位数量（未除以decimals）"""
        selector = "70a08231"  # balanceOf(address)
        data = "0x" + selector + self._pad_address(holder_address)
        result = self.eth_call(token_address, data)
        return int(result, 16)

    def get_reserves(self, pair_address):
        """调用 UniswapV2Pair 的 getReserves() 方法，返回 (reserve0, reserve1)"""
        selector = "0902f1ac"  # getReserves()
        try:
            result = self.eth_call(pair_address, "0x" + selector)
            if len(result) >= 130:
                reserve0 = int(result[2:66], 16)
                reserve1 = int(result[66:130], 16)
                return reserve0, reserve1
        except Exception as e:
            print(f"get_reserves failed: {e}")
        return None, None

    def token0(self, pair_address):
        """调用 UniswapV2Pair 的 token0() 方法"""
        selector = "0dfe1681"
        try:
            result = self.eth_call(pair_address, "0x" + selector)
            if len(result) >= 66:
                return "0x" + result[26:66]
        except Exception:
            pass
        return None

    def token1(self, pair_address):
        """调用 UniswapV2Pair 的 token1() 方法"""
        selector = "d21220a7"
        try:
            result = self.eth_call(pair_address, "0x" + selector)
            if len(result) >= 66:
                return "0x" + result[26:66]
        except Exception:
            pass
        return None

    def decimals(self, token_address, default=18):
        selector = "313ce567"  # decimals()
        try:
            result = self.eth_call(token_address, "0x" + selector)
            return int(result, 16)
        except Exception:
            return default

    def symbol(self, token_address):
        selector = "95d89b41"  # symbol()
        try:
            result = self.eth_call(token_address, "0x" + selector)
            hexstr = result[2:]
            if len(hexstr) <= 64:
                # 有些老合约把symbol编码成bytes32而非动态string
                raw = bytes.fromhex(hexstr)
                return raw.split(b"\x00")[0].decode("utf-8", errors="ignore").strip()
            length = int(hexstr[64:128], 16)
            strhex = hexstr[128:128 + length * 2]
            return bytes.fromhex(strhex).decode("utf-8", errors="ignore").strip("\x00")
        except Exception:
            return None
