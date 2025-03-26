async function loadUsersContract() {
  await loadContract("Users");
}

async function loadTransferOwnershipContract() {
  await loadContract("TransferOfOwnership");
}

async function loadPropertyContract() {
  await loadContract("Properties");
}

async function loadLandRegistryContract() {
  await loadContract("LandRegistry");
}

async function loadContract(contractName) {
  try {
      const response = await fetch(`http://127.0.0.1:8000/${contractName}.json`);
      if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status} for ${contractName}`);
      }
      const contractData = await response.json();

      const contractABI = contractData.abi;
      const networkId = Object.keys(contractData.networks)[0]; // Get first available network
      const contractAddress = contractData.networks[networkId]?.address || "UNKNOWN_ADDRESS";

      console.log(`${contractName} ABI:`, contractABI);
      console.log(`${contractName} Address:`, contractAddress);

      // Store in localStorage for later use
      localStorage.setItem(`${contractName}_ContractABI`, JSON.stringify(contractABI));
      localStorage.setItem(`${contractName}_ContractAddress`, contractAddress);
  } catch (error) {
      console.error(`Error loading ${contractName} contract:`, error);
  }
}

// Load contracts separately
loadUsersContract();
loadTransferOwnershipContract();
loadPropertyContract();
loadLandRegistryContract();


async function checkConnection()
{
    
  // checking Meta-Mask extension is added or not
  if (window.ethereum){

    try{
    //   await ethereum.enable();

      window.web3  = new Web3(ethereum);

      const accounts = await web3.eth.getAccounts();

      const accountConnectedToMetaMask = accounts[0];

      console.log("Account Connected to MetaMask:", accountConnectedToMetaMask);
      console.log("Account used to login        :",window.localStorage["employeeId"])
      console.log(accountConnectedToMetaMask != window.localStorage["employeeId"]);

      if( accountConnectedToMetaMask != window.localStorage["employeeId"])
      {
        alert("Mismatch in account used to login and connected to metamask.. Please login again");
        window.location.href = "/";
      }
      else
      {
        console.log("No Account changes detected !!");

        // fetch user details
        //fetchUserDetails();


        console.log("Revenue Dept ID:"+window.localStorage.revenueDepartmentId);

        document.getElementById("revenueDeptId").innerText = window.localStorage.revenueDepartmentId;

        document.getElementById('nameOfUser').innerText = window.localStorage.empName;

        // fetch properties 
        fetchPropertiesUnderControl(window.localStorage.revenueDepartmentId);

      }

    }catch(error){

      alert(error);

    }

  }else{
    alert("Please Add Metamask extension for your browser !!");
  }

}



async function fetchPropertiesUnderControl(revenueDepartmentId) {
  try {
      // ✅ Check if Web3 is available
      if (!window.web3) {
          throw new Error("Web3 provider is not available. Make sure MetaMask or another provider is connected.");
      }

      // ✅ Get contract details from localStorage
      let contractABI = localStorage.getItem("LandRegistry_ContractABI");
      console.log("contractABI: ", contractABI)
      let contractAddress = localStorage.getItem("LandRegistry_ContractAddress");
      console.log("contractAddress: ", contractABI)
      if (!contractABI || !contractAddress) {
          throw new Error("LandRegistry contract details are missing from localStorage.");
      }

      // ✅ Parse the ABI
      contractABI = JSON.parse(contractABI);

      // ✅ Initialize the contract
      let contract = new window.web3.eth.Contract(contractABI, contractAddress);

      // ✅ Get logged-in user
      let accountUsedToLogin = localStorage.getItem("employeeId");
      if (!accountUsedToLogin) {
          throw new Error("User is not logged in. Employee ID is missing.");
      }

      console.log(`Fetching properties for Revenue Dept ID: ${revenueDepartmentId}`);

      // ✅ Call the contract method with proper error handling
      let properties;
      try {
          properties = await contract.methods.getPropertiesByRevenueDeptId(revenueDepartmentId).call();
      } catch (contractError) {
          throw new Error(`Smart contract call failed: ${contractError.message}`);
      }

      console.log("Fetched properties:", properties);

      // ✅ Handle empty response
      if (!properties || properties.length === 0) {
          console.warn("No properties found for the given revenue department ID.");
          document.getElementById("propertiesTableBody").innerHTML = "<tr><td colspan='6'>No properties found.</td></tr>";
          return;
      }

      // ✅ Populate the table
      let tableBody = document.getElementById("propertiesTableBody");
      let tableBodyCode = "";

      for (let i = 0; i < properties.length; i++) {
          tableBodyCode += `
              <tr>
                  <td>${properties[i]["propertyId"]}</td>
                  <td>${properties[i]["locationId"]}</td>
                  <td>${properties[i]["surveyNumber"]}</td>
                  <td>${properties[i]["area"]}</td>
                  <td> <button class='pdfButton' onclick="showPdf(${properties[i]["propertyId"]})"> PDF </button></td>
                  <td>${handleStateOfProperty(properties[i])}</td>
              </tr>
          `;
      }

      tableBody.innerHTML = tableBodyCode;

  } catch (error) {
      console.error("Error fetching properties:", error);
      alert(`Error: ${error.message}`);
  }
}

  

async function acceptProperty(propertyId)
{
  let contractABI = JSON.parse(window.localStorage.LandRegistry_ContractABI);

  let contractAddress = window.localStorage.LandRegistry_ContractAddress;

  let contract = new window.web3.eth.Contract(contractABI,contractAddress);

  let accountUsedToLogin = window.localStorage["employeeId"];

  try{
  
    response = await contract.methods.verifyProperty(
                                            propertyId
                                            ).send({from:accountUsedToLogin})
                                            .then(function(value){
                                              return value;
                                            });
    console.log(response);

    fetchPropertiesUnderControl(window.localStorage.revenueDepartmentId);
 

  }
  catch(error)
  {
    console.log("Error");
    console.log(error);
  }
}


async function rejectProperty(propertyId)
{
  let contractABI = JSON.parse(window.localStorage.LandRegistry_ContractABI);

  let contractAddress = window.localStorage.LandRegistry_ContractAddress;

  let contract = new window.web3.eth.Contract(contractABI,contractAddress);

  let accountUsedToLogin = window.localStorage["employeeId"];

  try{
  
    response = await contract.methods.rejectProperty(
                                            propertyId,
                                            "Documents are Not clear"
                                            ).send({from:accountUsedToLogin})
                                            .then(function(value){
                                              return value;
                                            });
    console.log(response);
    fetchPropertiesUnderControl(window.localStorage.revenueDepartmentId);
 

  }
  catch(error)
  {
    console.log("Error");
    console.log(error);
  }
}


// function to create State of properties
function handleStateOfProperty(property)
{
    properyState = property["state"]

    // 0 => Created: uploaded by user.
    // 1 => Scheduled: Scheduled by Verifier for verification.
    // 2 => Verified: verified by verifier.
    // 3 => Rejected: rejected by verifier.
    // 4 => On Sale : On sale.
    // 5 => Bought : Sell to someon
    if(properyState == 0){
        htmlCode = "<button class='accept' onclick = acceptProperty("+
                    property["propertyId"]+")>Accept</button>"+
                    "<button class='reject'onclick = rejectProperty("+
                    property["propertyId"]+")>Reject</buttion>"
        ;
        return htmlCode;

    }
    else if(properyState == 1){
        return "Scheduled on"+property["scheduledDate"];
    }
    else if(properyState == 2 || properyState == 5 || properyState ==4 )
    {
        return "Accepted";
    }
    else if(properyState == 3)
    {
        let msg = "Rejected:"+property["rejectedReason"];
        return msg;
    }
    else
    {
        console.log("Invalid State")
        return "Invalid"
    }
}



// fucntion to show Registered pdfs
function showPdf(propertyId) {
    const frame = document.getElementById('pdf-frame');
    frame.src = `/propertiesDocs/pdf/${propertyId}`;
    
    const popup = document.querySelector('.pdf-popup');
    popup.style.display = 'block';
  }

function closePopup() {
const popup = document.querySelector('.pdf-popup');
popup.style.display = 'none';
}
