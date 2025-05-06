// SPDX-License-Identifier: MIT
pragma solidity >=0.4.22 <0.9.0;

contract Property {
    enum StateOfProperty {
        Created,
        Scheduled,
        Verified,
        Rejected,
        OnSale,
        Bought
    }

    struct Land {
        uint256 propertyId;
        uint256 locationId;
        uint256 revenueDepartmentId;
        uint256 surveyNumber;
        address owner;
        uint256 addressNo;
        uint256 postalCode;
        uint256 registeredTime;
        address employeeId;
        string scheduledDate;
        string rejectedReason;
        StateOfProperty state;
    }

    mapping(uint256 => Land) public lands;
    uint256 private landCount;

    event LandCreated(uint256 propertyId);
    event LandStateChanged(uint256 propertyId, StateOfProperty state);
    event LandUpdated(uint256 propertyId);
    event LandRemoved(uint256 propertyId);

    // Function to add a new land
    function addLand(
        uint256 _locationId,
        uint256 _revenueDepartmentId,
        uint256 _surveyNumber,
        address _owner,
        uint256 _addressNo
    ) public returns (uint256) {
        landCount++;

        lands[landCount] = Land({
            propertyId: landCount,
            locationId: _locationId,
            revenueDepartmentId: _revenueDepartmentId,
            surveyNumber: _surveyNumber,
            owner: _owner,
            addressNo: _addressNo,
            postalCode: 0,
            registeredTime: block.timestamp,
            employeeId: address(0),
            scheduledDate: "",
            rejectedReason: "",
            state: StateOfProperty.Created
        });

        // Emit the LandCreated event after adding the land
        emit LandCreated(landCount);

        return landCount;
    }

    

    // Function to get land details as a struct
    function getLandDetailsAsStruct(uint256 _propertyId) public view returns (Land memory) {
        require(lands[_propertyId].propertyId != 0, "Land does not exist");
        return lands[_propertyId];
    }

    // Function to change the state of land to Verified
    function changeStateToVerified(uint256 _propertyId, address _employeeId) public {
        require(lands[_propertyId].propertyId != 0, "Land does not exist");
        
        lands[_propertyId].employeeId = _employeeId;
        lands[_propertyId].state = StateOfProperty.Verified;
        
        emit LandStateChanged(_propertyId, StateOfProperty.Verified);
    }

     // Function to edit land details
    function editLand(
        uint256 _propertyId,
        uint256 _surveyNumber,
        uint256 _addressNo,
        uint256 _postalCode
    ) public {

        require(lands[_propertyId].propertyId != 0, "Land does not exist");
        require(lands[_propertyId].owner == msg.sender  , "Only owner can edit");
        require(_addressNo > 0, "addressNo must be greater than zero");

        lands[_propertyId].surveyNumber = _surveyNumber;
        lands[_propertyId].addressNo = _addressNo;
        lands[_propertyId].postalCode = _postalCode;

        emit LandUpdated(_propertyId);
    }

    // Function to remove land
    function removeLand(uint256 _propertyId) public {
        require(lands[_propertyId].propertyId != 0, "Land does not exist");
        require(lands[_propertyId].owner == msg.sender, "Only owner can remove");
        
        // Store property ID before deletion for event
        uint256 removedId = lands[_propertyId].propertyId;
        
        // Delete the land from mapping
        delete lands[_propertyId];
        
        emit LandRemoved(removedId);
    }

    // Function to change the state of land to Rejected
    function changeStateToRejected(uint256 _propertyId, address _employeeId, string memory _reason) public {
        require(lands[_propertyId].propertyId != 0, "Land does not exist");

        lands[_propertyId].employeeId = _employeeId;
        lands[_propertyId].state = StateOfProperty.Rejected;
        lands[_propertyId].rejectedReason = _reason;

        emit LandStateChanged(_propertyId, StateOfProperty.Rejected);
    }

    // Function to change the state of land to On Sale
    function changeStateToOnSale(uint256 _propertyId, address _owner) public {
        require(lands[_propertyId].propertyId != 0, "Land does not exist");
        require(lands[_propertyId].owner == _owner, "Only owner can make it available for sale");

        lands[_propertyId].state = StateOfProperty.OnSale;

        emit LandStateChanged(_propertyId, StateOfProperty.OnSale);
    }

    // Function to change the state of land back to Verified by the owner
    function changeStateBackToVerified(uint256 _propertyId, address _owner) public {
        require(lands[_propertyId].propertyId != 0, "Land does not exist");
        require(lands[_propertyId].owner == _owner, "Only owner is allowed");

        lands[_propertyId].state = StateOfProperty.Verified;

        emit LandStateChanged(_propertyId, StateOfProperty.Verified);
    }

    // Function to update the owner of the land and change state to Bought
   function updateOwner(uint256 _propertyId, address newOwner) public {
    require(_propertyId > 0, "Invalid property ID");
    require(newOwner != address(0), "Invalid new owner address");
    require(lands[_propertyId].propertyId != 0, "Land does not exist");
    require(newOwner != lands[_propertyId].owner, "New owner cannot be same as current owner");

    lands[_propertyId].owner = newOwner;
    lands[_propertyId].state = StateOfProperty.Bought;

    emit LandStateChanged(_propertyId, StateOfProperty.Bought);
}
}
