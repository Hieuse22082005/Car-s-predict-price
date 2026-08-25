from web3 import Web3
from fastapi import HTTPException

# Kết nối với node Blockchain Sepolia
SEPOLIA_RPC = "https://ethereum-sepolia-rpc.publicnode.com"
w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))

# Địa chỉ Contract của bạn
YOUR_CONTRACT_ADDRESS = "0x2169C854f514516038A068cCF758C2b8D40bCe01".lower()

def verify_transaction(txhash: str, expected_fee_eth: float):
    """
    Kiểm tra tính hợp lệ của txhash với số tiền kỳ vọng (ETH).
    """
    try:
        # 1. Lấy trạng thái giao dịch
        receipt = w3.eth.get_transaction_receipt(txhash)
        
        if receipt is None:
            raise HTTPException(status_code=400, detail="Giao dịch chưa được xác nhận trên Blockchain.")
            
        if receipt['status'] != 1:
            raise HTTPException(status_code=400, detail="Giao dịch đã bị lỗi (Reverted) trên mạng lưới.")

        # 2. Lấy thông tin chi tiết của giao dịch
        tx = w3.eth.get_transaction(txhash)

        # 3. Kiểm tra địa chỉ nhận (To Address)
        if tx['to'] is None or tx['to'].lower() != YOUR_CONTRACT_ADDRESS:
            raise HTTPException(status_code=400, detail="Giao dịch không gửi đến đúng địa chỉ hệ thống.")

        # 4. Kiểm tra số tiền thanh toán (Value)
        expected_fee_wei = w3.to_wei(expected_fee_eth, 'ether')
        if tx['value'] < expected_fee_wei:
            raise HTTPException(status_code=400, detail=f"Số tiền thanh toán không đủ. Yêu cầu tối thiểu: {expected_fee_eth} ETH.")

        return True

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Lỗi xác thực Blockchain: {str(e)}")