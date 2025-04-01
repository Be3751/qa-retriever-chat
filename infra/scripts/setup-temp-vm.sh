#!/bin/bash

RANDOM_SUFFIX="6j8b0"
RESOURCE_GROUP="qachat-rg-$RANDOM_SUFFIX"
AI_SEARCH_NAME="qachat-ais-$RANDOM_SUFFIX"
OPENAI_SERVICE_NAME="qachat-aoai-$RANDOM_SUFFIX"
APP_SERVICE_PLAN_NAME="qachat-asp-$RANDOM_SUFFIX"
APP_SERVICE_NAME="qachat-as-$RANDOM_SUFFIX"

LOCATION="japaneast"
VNET_NAME="qachat-vn-$RANDOM_SUFFIX"
SUBNET_NAME="qachat-sbn-$RANDOM_SUFFIX"
SUBNET_PREFIX="10.0.5.0/24" 
VM_NAME="qachat-temp-vm-$RANDOM_SUFFIX"
VM_IMAGE="Ubuntu2204" 
ADMIN_USERNAME="azureuser"
SSH_KEY_PATH="$HOME/.ssh/id_rsa.pub"

# Cloud-init script to install Azure CLI and additional software
CLOUD_INIT_SCRIPT=$(cat <<EOF
#cloud-config
package_update: true
packages:
  - curl
  - apt-transport-https
  - lsb-release
  - gnupg
  - git          
runcmd:
  - curl -sL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
  - mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
  - echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $(lsb_release -cs) main" > /etc/apt/sources.list.d/azure-cli.list
  - apt-get update
  - apt-get install -y azure-cli
EOF
)

# Create subnet in the existing virtual network
echo "Creating subnet in the existing virtual network..."
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $SUBNET_NAME \
  --address-prefix $SUBNET_PREFIX

# Create virtual machine
echo "Creating virtual machine..."
az vm create \
  --resource-group $RESOURCE_GROUP \
  --name $VM_NAME \
  --image $VM_IMAGE \
  --vnet-name $VNET_NAME \
  --subnet $SUBNET_NAME \
  --admin-username $ADMIN_USERNAME \
  --ssh-key-values $SSH_KEY_PATH \
  --custom-data <(echo "$CLOUD_INIT_SCRIPT")

# Open port 22 for SSH
echo "Opening port 22 for SSH..."
az vm open-port --port 22 --resource-group $RESOURCE_GROUP --name $VM_NAME

# Get public IP of the VM
VM_IP=$(az vm list-ip-addresses --resource-group $RESOURCE_GROUP --name $VM_NAME --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)

echo "Temporary VM setup complete."
echo "You can SSH into the VM using the following command:"
echo "ssh $ADMIN_USERNAME@$VM_IP"

# Cleanup instructions
echo "To delete the virtual machine, run the following command:"
echo "az vm delete --resource-group $RESOURCE_GROUP --name $VM_NAME --yes --no-wait"
