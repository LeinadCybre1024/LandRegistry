async function loadUsersContract() {
  await loadContract("Users");
}

async function loadTransferOwnershipContract() {
  await loadContract("TransferOfOwnerShip");
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



async function connectToBlockchain() {

  // checking Meta-Mask extension is added or not
  if (window.ethereum) {

    window.web3 = new Web3(ethereum);


    try {
      // await ethereum.enable();

      alertUser('','alert-info','none');
      showTransactionLoading();

      await window.ethereum.request({
        method: "wallet_requestPermissions",
        params: [
          {
            eth_accounts: {}
          }
        ]
      });


      const accounts = await web3.eth.getAccounts();
      window.localStorage.setItem("employeeId", accounts[0]);

      window.employeeId = accounts[0];

      loadingDiv = document.getElementById("loadingDiv");
      loadingDiv.style.color = "green";
      loadingDiv.innerHTML = `Connected with : ${accounts[0]}
                                <br>
                                Enter Password
                                `;

      
      document.getElementById("connectToBlockchainDiv").style.display = "none";
      document.getElementById("passwordDiv").style.display = "block";

      closeTransactionLoading();
      alertUser('Enter Your Password','alert-success','block');


    } catch (error) {
      console.log(error);
      closeTransactionLoading();
      alertUser(showError(error),'alert-danger','block');
    }

  } else {
    alertUser('Please Add Metamask extension for your browser !!','alert-danger','block');
  }

}



function login() {
  let employeeId = window.localStorage["employeeId"];
  let password = document.getElementById("password").value;


  // Create a new FormData object
  const formData = new FormData();

  // Append the files and data to the FormData object
  formData.append('employeeId', employeeId);
  formData.append('password', password);

  // Send a POST request to the Flask server
  fetch('/login', {
    method: 'POST',
    body: formData
  })
    .then(response => response.json())
    .then(data => {
      // Handle the response from the Flask server
      console.log(data);

      let status = data['status'];
      let msg = data['msg'];


      if (status == 1) {
        console.log(msg);
        // change
        let revenueDepartmentId = data["revenueDepartmentId"];
        window.localStorage.revenueDepartmentId = revenueDepartmentId;
        window.localStorage.empName = data['empName'];
        window.location.href = "/dashboard";
      }
      else {
        console.log(msg)
        alertUser(msg,'alert-danger','block');
      }

    })
    .catch(error => {
      // Handle any errors that occur during the request
      console.error(error);
    });

}







function showTransactionLoading() {

  loadingDiv = document.getElementById("loadingDiv");

  loadingDiv.style.display = "block";
}

function closeTransactionLoading() {
  loadingDiv = document.getElementById("loadingDiv");

  loadingDiv.style.display = "none";
}

// show error reason to user
function showError(errorOnTransaction) {


  errorCode = errorOnTransaction.code;

  if(errorCode==4001){
    return "Rejected Transaction";
  }
  else{
    let start = errorOnTransaction.message.indexOf('{');
    let end = -1;
  
    errorObj = JSON.parse(errorOnTransaction.message.slice(start, end));
  
    errorObj = errorObj.value.data.data;
  
    txHash = Object.getOwnPropertyNames(errorObj)[0];
  
    let reason = errorObj[txHash].reason;
  
    return reason;
  }
}


function alertUser(msg,msgType,display){

  console.log(msg,display);
  notifyUser = document.getElementById("notifyUser");

  notifyUser.classList = [];
  notifyUser.classList.add("alert");
  notifyUser.classList.add(msgType);
  notifyUser.innerText = msg;
  notifyUser.style.display = display;


  
}

