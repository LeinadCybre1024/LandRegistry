const Users = artifacts.require("Users");
const Properties = artifacts.require("Properties");
const LandRegistry = artifacts.require("LandRegistry");
const TransferOfOwnership = artifacts.require("TransferOfOwnership");

module.exports = async function(deployer) {
  // Deploy Users contract
  await deployer.deploy(Users);
  const usersInstance = await Users.deployed();

  // Deploy Properties contract
  await deployer.deploy(Properties);
  const propertiesInstance = await Properties.deployed();

  // Deploy LandRegistry contract with the address of the deployed Users contract
  await deployer.deploy(LandRegistry, usersInstance.address);
  const landRegistryInstance = await LandRegistry.deployed();

  // Deploy TransferOfOwnership contract with the address of the deployed LandRegistry contract
  await deployer.deploy(TransferOfOwnership, landRegistryInstance.address);
};
