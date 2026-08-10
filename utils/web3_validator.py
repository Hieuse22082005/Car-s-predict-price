from web3 import Web3
from fastapi import HTTPException

# Kết nối với node Blockchain (Ví dụ dùng BSC Testnet hoặc Mainnet)
# Bạn có thể lấy RPC URL miễn phí từ Infura, Alchemy hoặc public RPC
SEPOLIA_RPC = "https://ethereum-sepolia-rpc.publicnode.com"
w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
# Cấu hình của bạn
YOUR_CONTRACT_ADDRESS = "0x2B6F37e09682a26a5689D8A178e27bd0aE973E1C".lower()
EXPECTED_FEE_BNB = 0.001 # Phí định giá
EXPECTED_FEE_WEI = w3.to_wei(EXPECTED_FEE_BNB, 'ether')

def verify_transaction(txhash: str):
    """
    Kiểm tra tính hợp lệ của txhash từ mạng lưới blockchain.
    """
    try:
        # 1. Lấy trạng thái (receipt) của giao dịch
        # Dùng để biết giao dịch đã được đào (mined) và thành công chưa
        receipt = w3.eth.get_transaction_receipt(txhash)
        
        if receipt is None:
            raise HTTPException(status_code=400, detail="Giao dịch chưa được xác nhận trên Blockchain.")
            
        if receipt['status'] != 1:
            raise HTTPException(status_code=400, detail="Giao dịch đã bị lỗi (Reverted) trên mạng lưới.")

        # 2. Lấy thông tin chi tiết của giao dịch (ai gửi, gửi cho ai, bao nhiêu tiền)
        tx = w3.eth.get_transaction(txhash)

        # 3. Kiểm tra địa chỉ nhận (To Address)
        # Bắt buộc phải là địa chỉ ví hoặc Smart Contract của bạn
        if tx['to'].lower() != YOUR_CONTRACT_ADDRESS:
            raise HTTPException(status_code=400, detail="Giao dịch không gửi đến đúng địa chỉ hệ thống.")

        # 4. Kiểm tra số tiền thanh toán (Value)
        # Lưu ý: Nếu gọi hàm Smart Contract, phần value có thể nằm trong msg.value
        if tx['value'] < EXPECTED_FEE_WEI:
            raise HTTPException(status_code=400, detail="Số tiền thanh toán không đủ để định giá.")

        return True

    except Exception as e:
        # Bắt lỗi chuẩn nếu mã txhash sai định dạng (không phải 66 ký tự hex)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Lỗi xác thực Blockchain: {str(e)}")