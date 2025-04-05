// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

contract Users {
    struct User {
        address userID;
        string firstName;
        string lastName;
        string dateOfBirth;
        string idNumber;
        uint256 accountCreatedDateTime;
    }

    mapping(address => bool) private registeredUsers;
    mapping(address => User) public users;
    mapping(string => bool) private idNumbers;
    
    event UserRegistered(address indexed userID, uint256 indexed accountCreatedDateTime);

    function registerUser(
        string memory _firstName,
        string memory _lastName,
        string memory _dateOfBirth,
        string memory _idNumber
    ) public {
        require(registeredUsers[msg.sender] == false, "User already registered");
        require(idNumbers[_idNumber] == false, "ID number already registered");

        User memory newUser = User({
            userID: msg.sender,
            firstName: _firstName,
            lastName: _lastName,
            dateOfBirth: _dateOfBirth,
            idNumber: _idNumber,
            accountCreatedDateTime: block.timestamp
        });

        users[msg.sender] = newUser;
        registeredUsers[msg.sender] = true;
        idNumbers[_idNumber] = true;

        emit UserRegistered(msg.sender, block.timestamp);
    }

    function getUserDetails(address _userId) public view returns (
        string memory firstName, 
        string memory lastName, 
        string memory dateOfBirth, 
        string memory idNumber,
        uint256 accountCreated
    ) {
        require(users[_userId].userID != address(0), "User does not exist");
        User storage user = users[_userId];
        return (
            user.firstName, 
            user.lastName, 
            user.dateOfBirth, 
            user.idNumber,
            user.accountCreatedDateTime
        );
    }
}