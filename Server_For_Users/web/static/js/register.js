async function loadUsersContract() {
  await loadContract("Users");
}

async function loadTransferOwnershipContract() {
  await loadContract("TransferOwnership");
}

async function loadPropertyContract() {
  await loadContract("Property");
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

      const account = accounts[0];

      console.log("Connected To metamask:", account);
      console.log("Account Used to Login:",window.localStorage["userAddress"])
      console.log(account != window.localStorage["userAddress"]);

      if( account != window.localStorage["userAddress"])
      {
        alert("wrong account detected..!! please connect again");

        window.location.href = "/";
      }
      else
      {
        console.log("No Account changes detected !!");

        alertUser(`Wallet Connected : <span id="connectedAccount">${account.slice(0,6)}...${account.slice(-4)} </span>`,'alert-success','block');
      }

    }catch(error){

      alert(error);

    }

  }else{
    alert("Please Add Metamask extension for your browser !!");
  }

}


async function registerUser(event) {
  event.preventDefault();

  console.log("Register User function called");

  alertUser("", "alert-info", "none");

  let fname = document.getElementById("firstName").value;
  let lname = document.getElementById("lastName").value;
  let dob = document.getElementById("dob").value;
  let aadharNo = document.getElementById("aadharNo").value;

  console.log(`Inputs: ${fname}, ${lname}, ${dob}, ${aadharNo}`);

  let contractABI, contractAddress;

  try {
    contractABI = JSON.parse(window.localStorage.Users_ContractABI);
    contractAddress = window.localStorage.Users_ContractAddress;
  } catch (error) {
    console.error("Error loading contract from localStorage:", error);
    alertUser("Error loading contract. Try again later.", "alert-danger", "block");
    return;
  }

  console.log("Contract Loaded:", contractABI, contractAddress);

  if (!contractABI || !contractAddress) {
    alertUser("Smart contract details missing!", "alert-danger", "block");
    return;
  }

  window.contract = new window.web3.eth.Contract(contractABI, contractAddress);

  let accountUsedToLogin = window.localStorage["userAddress"];

  try {
    const accounts = await web3.eth.getAccounts();
    const connectedAccountToMetaMask = accounts[0];

    console.log("Connected Account:", connectedAccountToMetaMask);
    console.log("Expected Account:", accountUsedToLogin);

    if (connectedAccountToMetaMask !== accountUsedToLogin) {
      alertUser(
        `Account Mismatch! Please connect ${accountUsedToLogin.slice(0, 6)}...${accountUsedToLogin.slice(-4)}`,
        "alert-warning",
        "block"
      );
      return;
    }

    console.log("Calling registerUser on smart contract with values:", fname, lname, dob, aadharNo);

    showTransactionLoading("Registering User...");

    const tx = await contract.methods
      .registerUser(fname, lname, dob, aadharNo)
      .send({ from: accountUsedToLogin, gas: 5000000 }) // Increased gas limit for execution
      .on("transactionHash", function (hash) {
        console.log("Transaction Hash:", hash);
      })
      .on("receipt", function (receipt) {
        console.log("Transaction Mined! Receipt:", receipt);
      })
      .on("confirmation", function (confirmationNumber, receipt) {
        console.log(`Transaction confirmed (${confirmationNumber} confirmations)`, receipt);
      })
      .on("error", function (error, receipt) {
        console.error("Blockchain Error:", error);
        if (receipt) {
          console.error("Transaction Receipt:", receipt);
        }
      });

    console.log("Transaction Success:", tx);

    let userDetails = await contract.methods.users(accountUsedToLogin).call();

    console.log("User Details from contract:", userDetails);

    if (userDetails["userID"] === accountUsedToLogin) {
      console.log("Registered Successfully");
      showTransactionLoading(`Registered Successfully <br> Redirecting to Dashboard`);
      window.location.href = "/dashboard";
    } else {
      closeTransactionLoading();
      alertUser(`Registration Failed! Try again`, "alert-danger", "block");
    }
  } catch (error) {
    console.error("Transaction Error:", error);

    if (error.receipt) {
      console.error("Transaction Receipt:", error.receipt);
    }

    const reason = showError(error);
    closeTransactionLoading();
    alertUser(reason, "alert-danger", "block");
  }
}




function showTransactionLoading(msg) {

  loadingDiv = document.getElementById("loadingDiv");

  loadingDiv.children[0].innerHTML = msg;

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
  notifyUser.innerHTML = msg;
  notifyUser.style.display = display;


  
}

