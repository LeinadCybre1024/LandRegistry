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


async function connectToBlockchain() {
    const notifyUser = document.getElementById("notifyUser");

    console.log("🔍 Checking if MetaMask is installed...");

    if (window.ethereum) {
        console.log("✅ MetaMask detected. Initializing Web3...");
        window.web3 = new Web3(window.ethereum);

        try {
            console.log("🔄 Requesting wallet connection...");
            showTransactionLoading();

            // Request permission to access accounts
            await window.ethereum.request({
                method: "wallet_requestPermissions",
                params: [{ eth_accounts: {} }]
            });

            console.log("🔄 Fetching user accounts...");
            const accounts = await web3.eth.getAccounts();

            if (accounts.length === 0) {
                throw new Error("🚫 No accounts found. User may have denied connection.");
            }

            console.log(`✅ Connected to account: ${accounts[0]}`);
            window.localStorage.setItem("userAddress", accounts[0]);
            window.userAddress = accounts[0];

            // Retrieve contract details from local storage
            console.log("🔍 Fetching contract details...");
            let contractABI = JSON.parse(window.localStorage.Users_ContractABI || "null");
            let contractAddress = window.localStorage.Users_ContractAddress || null;

            if (!contractABI || !contractAddress) {
                throw new Error("🚫 Contract details not found in local storage.");
            }

            console.log("✅ Contract ABI:", contractABI);
            console.log(`✅ Contract Address: ${contractAddress}`);

            let contract = new window.web3.eth.Contract(contractABI, contractAddress);

            try {
                console.log(`🔍 Checking if user is registered...`);
                
                let userDetails = await contract.methods.users(accounts[0]).call();
                
                console.log("✅ User details fetched:", userDetails);
            
                const loadingDiv = document.getElementById("loadingDiv");
                loadingDiv.style.color = "green";
            
                // Check if userDetails is valid
                if (userDetails && userDetails["userID"] && userDetails["userID"] === accounts[0]) {
                    console.log("✅ User is already registered. Redirecting to login...");
                    loadingDiv.innerHTML = `Connected with: ${accounts[0]}<br>Redirecting to Login...`;
                    window.location.href = "/dashboard";
                } else {
                    console.warn("🚫 User details are empty or null. Redirecting to register...");
                    loadingDiv.innerHTML = `Connected with: ${accounts[0]}<br>Redirecting to Register page...`;
                    window.location.href = "/register";
                }
            } catch (contractError) {
                console.error("🚨 Error fetching user details:", contractError);
                notifyUser.innerText = showError(contractError);
                notifyUser.style.display = "block";
            }

        } catch (error) {
            console.error("❌ Connection failed:", error);
            notifyUser.innerText = showError(error);
            notifyUser.style.display = "block";
        }
    } else {
        console.warn("⚠️ MetaMask is not installed!");
        notifyUser.classList.add("alert-danger");
        notifyUser.style.display = "block";
        notifyUser.innerText = "Please install MetaMask to use this feature!";
    }
}


function showTransactionLoading() {
    console.log("Displaying transaction loading screen...");
    const loadingDiv = document.getElementById("loadingDiv");
    loadingDiv.style.display = "block";
}

function closeTransactionLoading() {
    console.log("Hiding transaction loading screen...");
    const loadingDiv = document.getElementById("loadingDiv");
    loadingDiv.style.display = "none";
}

// Show error reason to the user
function showError(errorOnTransaction) {
    console.log("Handling error:", errorOnTransaction);

    try {
        let start = errorOnTransaction.message.indexOf('{');
        let end = -1;

        let errorObj = JSON.parse(errorOnTransaction.message.slice(start, end));

        if (errorObj && errorObj.value && errorObj.value.data) {
            let txHash = Object.getOwnPropertyNames(errorObj.value.data.data)[0];
            let reason = errorObj.value.data.data[txHash].reason;
            console.log("Error reason extracted:", reason);
            return reason;
        }
    } catch (parseError) {
        console.error("Failed to parse error message:", parseError);
    }

    return errorOnTransaction.message || "Unknown error occurred.";
}

