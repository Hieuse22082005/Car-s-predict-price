// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract CarPayment {
    address public owner;
    uint256 public fee = 0.001 ether; // Phí định giá tương đương 0.001 ETH/BNB

    // Hàm này chạy 1 lần duy nhất lúc Deploy để ghi nhận ví của bạn là chủ két sắt
    constructor() {
        owner = msg.sender;
    }

    // 1. KHE NHÉT TIỀN: Khách hàng gọi hàm này để thanh toán
    function payForValuation() public payable {
        require(msg.value >= fee, "Khong du 0.001 ETH de thanh toan");
    }

    // 2. MỞ KÉT RÚT TIỀN: Chỉ ví của bạn mới gọi được hàm này
    function withdraw() public {
        require(msg.sender == owner, "Chi chu so huu moi duoc rut tien");
        
        uint256 balance = address(this).balance;
        require(balance > 0, "Ket sat dang trong rong");

        // Lệnh chuyển toàn bộ tiền trong Contract về ví của bạn
        (bool success, ) = owner.call{value: balance}("");
        require(success, "Rut tien that bai");
    }

    // 3. KIỂM TRA SỐ DƯ: Xem két sắt đang chứa bao nhiêu tiền (Ai cũng xem được)
    function getContractBalance() public view returns (uint256) {
        return address(this).balance;
    }
}