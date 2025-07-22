curl -s $1/save

cd /
if [ $2 = allreadytoinstall ]; then
    echo "server + ui update"
    curl -sL -o server.zip https://github.com/hendriksen-mark/raspberry_extension_server/archive/$3.zip
    unzip -qo server.zip
    rm server.zip

    python3 -m pip install --upgrade pip
    python3 -m pip install --upgrade pip --break-system-packages
    pip3 install -r raspberry_extension_server-$3/requirements.txt --no-cache-dir --break-system-packages

    cp -r raspberry_extension_server-$3/BridgeEmulator/flaskUI /opt/raspberry_extension_server/
    cp -r raspberry_extension_server-$3/BridgeEmulator/ServerObjects /opt/raspberry_extension_server/
    cp -r raspberry_extension_server-$3/BridgeEmulator/services /opt/raspberry_extension_server/
    cp -r raspberry_extension_server-$3/BridgeEmulator/configManager /opt/raspberry_extension_server/
    cp -r raspberry_extension_server-$3/BridgeEmulator/api.py /opt/raspberry_extension_server/
    cp -r raspberry_extension_server-$3/BridgeEmulator/githubInstall.sh /opt/raspberry_extension_server/
    rm -r raspberry_extension_server-$3
else
    echo "ui update"
fi

mkdir raspberry_extension_server_ui
curl -sL https://github.com/hendriksen-mark/raspberry_extension_server_ui/releases/latest/download/raspberry_extension_server_ui-release.zip -o serverUI.zip
unzip -qo serverUI.zip -d raspberry_extension_server_ui
rm serverUI.zip
cp -r raspberry_extension_server_ui/dist/index.html /opt/raspberry_extension_server/flaskUI/templates/
cp -r raspberry_extension_server_ui/dist/assets /opt/raspberry_extension_server/flaskUI/
rm -r raspberry_extension_server_ui

curl -s $1/restart
