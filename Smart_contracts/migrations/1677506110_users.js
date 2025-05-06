const Users = artifacts.require("Users");
const Property = artifacts.require("Property");
const LandRegistry = artifacts.require("LandRegistry");
const TransferOfOwnership = artifacts.require("TransferOfOwnership");

module.exports = async function(deployer) {
  // Deploy Users contract
  await deployer.deploy(Users);
  const usersInstance = await Users.deployed();

  // Deploy Properties contract
  await deployer.deploy(Property);
  const propertiesInstance = await Property.deployed();

  // Deploy LandRegistry contract with the addresses of the deployed Users and Property contracts
  await deployer.deploy(LandRegistry, usersInstance.address, propertiesInstance.address);
  const landRegistryInstance = await LandRegistry.deployed();

  // Deploy TransferOfOwnership contract with the address of the deployed LandRegistry contract
  await deployer.deploy(TransferOfOwnership, landRegistryInstance.address);
};
