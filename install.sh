#!/usr/bin/env bash

arch=`uname -m`

cd /tmp

### Choose Branch for Install
echo -e "\033[36mFetching available branches...\033[0m"

# Fetch branches from GitHub API
branches_json=$(curl -s https://api.github.com/repos/hendriksen-mark/raspberry_extension_server/branches)

# Check if curl was successful
if [ $? -ne 0 ] || [ -z "$branches_json" ]; then
    echo -e "\033[31mError: Could not fetch branches from GitHub. Using default branches.\033[0m"
    branches=("main" "dev")
else
    # Parse branch names from JSON using grep and sed
    branches=($(echo "$branches_json" | grep '"name":' | sed 's/.*"name": *"\([^"]*\)".*/\1/'))
fi

# Display available branches
echo -e "\033[36mPlease choose a Branch to install\033[0m"
echo -e "\033[33mSelect Branch by entering the corresponding Number: [Default: ${branches[0]}]\033[0m"

for i in "${!branches[@]}"; do
    branch_name="${branches[$i]}"
    case $branch_name in
        "main"|"master")
            echo -e "[$((i+1))] $branch_name - most stable Release"
            ;;
        "dev"|"development")
            echo -e "[$((i+1))] $branch_name - test latest features and fixes - Work in Progress!"
            ;;
        *)
            echo -e "[$((i+1))] $branch_name"
            ;;
    esac
done

echo -e "\033[36mNote: Please report any Bugs or Errors with Logs to our GitHub, Discourse or Slack. Thank you!\033[0m"
echo -n "I go with Nr.: "

branchSelection=""
read userSelection

# Validate user input and set branch selection
if [[ "$userSelection" =~ ^[0-9]+$ ]] && [ "$userSelection" -ge 1 ] && [ "$userSelection" -le "${#branches[@]}" ]; then
    branchSelection="${branches[$((userSelection-1))]}"
    echo -e "$branchSelection selected"
else
    branchSelection="${branches[0]}"
    echo -e "Invalid selection. Using default: $branchSelection"
fi

# Check for Python 3
if ! command -v python3 &>/dev/null; then
    apt-get install -y python3 python3-pip
fi

echo "https://github.com/hendriksen-mark/raspberry_extension_server/archive/$branchSelection.zip"
# installing Raspberry Extension Server
echo -e "\033[36m Installing Raspberry Extension Server.\033[0m"
curl -sL https://github.com/hendriksen-mark/raspberry_extension_server/archive/$branchSelection.zip -o server.zip
unzip -qo server.zip
cd raspberry_extension_server-$branchSelection/

echo -e "\033[36m Installing Python Dependencies.\033[0m"
python3 -m pip install --upgrade pip --break-system-packages
pip3 install -r requirements.txt --break-system-packages


if [ -d "/opt/raspberry_extension_server" ]; then

  systemctl stop raspberry_extension_server.service
  echo -e "\033[33m Existing installation found, performing upgrade.\033[0m"

  cp -r /opt/raspberry_extension_server/config /tmp/raspberry_extension_server_backup
  rm -rf /opt/raspberry_extension_server/*
  cp -r /tmp/raspberry_extension_server_backup /opt/raspberry_extension_server/config

else
  if cat /proc/net/tcp | grep -c "00000000:0050" > /dev/null; then
      echo -e "\033[31m ERROR!! Port 80 already in use. Close the application that use this port and try again.\033[0m"
      exit 1
  fi
  if cat /proc/net/tcp | grep -c "00000000:01BB" > /dev/null; then
      echo -e "\033[31m ERROR!! Port 443 already in use. Close the application that use this port and try again.\033[0m"
      exit 1
  fi
  mkdir /opt/raspberry_extension_server
fi


cp -r flaskUI /opt/raspberry_extension_server/
cp -r ServerObjects /opt/raspberry_extension_server/
cp -r services /opt/raspberry_extension_server/
cp -r configManager /opt/raspberry_extension_server/
cp -r api.py /opt/raspberry_extension_server/
cp -r githubInstall.sh /opt/raspberry_extension_server/

# Copy web interface files

curl -sL https://github.com/hendriksen-mark/raspberry_extension_server_ui/releases/latest/download/raspberry_extension_server_ui-release.zip -o serverUI.zip
unzip -qo serverUI.zip
mv dist/index.html /opt/raspberry_extension_server/flaskUI/templates/
cp -r dist/assets /opt/raspberry_extension_server/flaskUI/
rm -r dist

# Update service file with selected branch
sed "s/Environment=branch=.*/Environment=branch=$branchSelection/" raspberry_extension_server.service > /tmp/raspberry_extension_server.service
cp /tmp/raspberry_extension_server.service /lib/systemd/system/raspberry_extension_server.service
cd ../../
rm -rf serverUI.zip raspberry_extension_server_ui-$branchSelection
chmod 644 /lib/systemd/system/raspberry_extension_server.service
systemctl daemon-reload
systemctl enable raspberry_extension_server.service
systemctl start raspberry_extension_server.service

echo -e "\033[32m Installation completed.\033[0m"
