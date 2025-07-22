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


echo -e "\033[36mPlease choose a install method\033[0m"
echo -e "\033[33mSelect Install Method by entering the corresponding Number: [Default: 1]\033[0m"
echo -e "[1] Install as host service (Recommended)"
echo -e "[2] Install with Docker"
echo -n "I go with Nr.: "
installMethod=""
read installMethod

if [[ "$installMethod" =~ ^[1-2]$ ]]; then
    echo -e "Install method $installMethod selected"
else
    installMethod="1"
    echo -e "Invalid selection. Using default: $installMethod"
fi

case $installMethod in
        1)
        installMethod="host"
        echo -e "Host selected"
        ;;
        2)
        installMethod="docker"
        echo -e "Docker selected"
        ;;
				*)
        installMethod="host"
        echo -e "Host selected"
        ;;
esac

if [ "$installMethod" == "host" ]; then
  echo -e "\033[36mInstalling Raspberry Extension Server as host service.\033[0m"
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
else
    echo -e "\033[36mInstalling Raspberry Extension Server with Docker.\033[0m"
    if ! command -v docker &>/dev/null; then
        echo -e "\033[31mDocker is not installed. Installing Docker.\033[0m"
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo apt-get -y install libffi-dev libssl-dev python3-dev python3 python3-pip
    else
        echo -e "\033[32mDocker is already installed.\033[0m"
    fi
    interface=$(ip route | grep default | awk '{print $5}')
    ip=`ip addr show $interface | grep 'inet ' | awk '{print $2}' | cut -d/ -f1`
    ARCH=$(uname -m)
    PLATFORM=""

    case "$ARCH" in
      armv7l)  PLATFORM="linux/arm/v7" ;;
      armv6l)  PLATFORM="linux/arm/v6" ;;
      aarch64) PLATFORM="linux/arm64" ;;
      x86_64)  PLATFORM="linux/amd64" ;;
      i386|i686) PLATFORM="linux/386" ;;
      *)       PLATFORM="linux/$ARCH" ;;
    esac

    echo -e "\033[36m Platform: $PLATFORM\033[0m"
    echo -e "\033[36m IP: $ip\033[0m"
    curl -sL https://github.com/hendriksen-mark/raspberry_extension_server/archive/$branchSelection.zip -o server.zip
    unzip -qo server.zip
    cd raspberry_extension_server-$branchSelection/
    docker stop raspberry_extension_server
    docker rm raspberry_extension_server
    docker buildx create --name mybuilder --use
    docker buildx inspect --bootstrap
    docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
    docker buildx build --builder mybuilder --platform=$PLATFORM --build-arg TARGETPLATFORM=$PLATFORM --cache-from=type=local,src=/tmp/.buildx-cache --cache-to=type=local,dest=/tmp/.buildx-cache -t raspberry_extension_server/raspberry_extension_server:ci -f ./.build/Dockerfile --load .
    docker run -d --name raspberry_extension_server --privileged --network=host -v /opt/raspberry_extension_server/config:/opt/hue-emulator/config -e IP=$ip -e DEBUG=true raspberry_extension_server/raspberry_extension_server:ci
    cd ..
    rm -rf server.zip raspberry_extension_server_ui-$branchSelection
fi

echo -e "\033[32m Installation completed.\033[0m"
