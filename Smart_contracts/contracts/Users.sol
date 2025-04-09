// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

contract Users {
    struct User {
        address userID;
        string firstName;
        string lastName;
        string idNumber;
        uint256 accountCreatedDateTime;
    }

    address public owner;
    uint256 public registrationFee = 0.01 ether;
    
    // Track fee payments separately from registration status
    mapping(address => bool) private feePayments;
    mapping(address => bool) private registeredUsers;
    mapping(address => User) public users;
    mapping(string => bool) private idNumbers;
    
    event UserRegistered(address indexed userID, uint256 indexed accountCreatedDateTime);
    event FeeReceived(address indexed payer, uint256 amount);
    event FeeChanged(uint256 newFee);
    event FundsWithdrawn(address indexed owner, uint256 amount);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    /**
     * @dev Allows users to pay the registration fee
     * @notice Payment must be exact amount of current registrationFee
     * @notice User cannot have already paid or registered
     */
    function payRegistrationFee() external payable {
      //  require(!feePayments[msg.sender], "Fee already paid");
        require(!registeredUsers[msg.sender], "Already registered");
        require(msg.value == registrationFee, "Incorrect fee amount");
        
        feePayments[msg.sender] = true;
        emit FeeReceived(msg.sender, msg.value);
    }

    /**
     * @dev Registers a new user after fee payment verification
     * @param _firstName User's first name
     * @param _lastName User's last name
     * @param _idNumber Government-issued ID number
     */
    function registerUser(
        string memory _firstName,
        string memory _lastName,
        string memory _idNumber
    ) public {
        // Verify fee payment
        //require(feePayments[msg.sender], "Registration fee not paid");
        
        // Original validation checks
        require(!registeredUsers[msg.sender], "User already registered");
        require(bytes(_firstName).length > 0, "First name cannot be empty");
        require(bytes(_lastName).length > 0, "Last name cannot be empty");
        require(bytes(_idNumber).length > 0, "ID number cannot be empty");
        require(!idNumbers[_idNumber], "ID number already registered");

        // Create user record
        users[msg.sender] = User({
            userID: msg.sender,
            firstName: _firstName,
            lastName: _lastName,
            idNumber: _idNumber,
            accountCreatedDateTime: block.timestamp
        });

        registeredUsers[msg.sender] = true;
        idNumbers[_idNumber] = true;

        emit UserRegistered(msg.sender, block.timestamp);
    }

    // ========== HELPER FUNCTIONS ========== //

    function getUserDetails(address _userId) public view returns (
        string memory firstName, 
        string memory lastName,  
        string memory idNumber,
        uint256 accountCreated
    ) {
        require(users[_userId].userID != address(0), "User does not exist");
        User storage user = users[_userId];
        return (
            user.firstName, 
            user.lastName, 
            user.idNumber,
            user.accountCreatedDateTime
        );
    }

    function hasPaidFee(address _user) public view returns (bool) {
        return feePayments[_user];
    }

    function isRegistered(address _user) public view returns (bool) {
        return registeredUsers[_user];
    }

    // ========== ADMIN FUNCTIONS ========== //

    function setRegistrationFee(uint256 _newFee) external onlyOwner {
        require(_newFee != registrationFee, "Fee is already this value");
        registrationFee = _newFee;
        emit FeeChanged(_newFee);
    }

    function withdrawFees(address payable _to) external onlyOwner {
        require(_to != address(0), "Invalid withdrawal address");
        uint256 balance = address(this).balance;
        require(balance > 0, "No fees to withdraw");
        
        (bool success, ) = _to.call{value: balance}("");
        require(success, "Withdrawal failed");
        
        emit FundsWithdrawn(_to, balance);
    }

    // Emergency stop pattern
    bool public registrationsPaused;

    modifier whenNotPaused() {
        require(!registrationsPaused, "Registrations are paused");
        _;
    }

    function pauseRegistrations() external onlyOwner {
        registrationsPaused = true;
    }

    function unpauseRegistrations() external onlyOwner {
        registrationsPaused = false;
    }
}