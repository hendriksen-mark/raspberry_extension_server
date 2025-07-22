# This image just moves the correct bins to a specific folder.
# Can also be used to compile the binaries (for an even better experience)
FROM busybox AS binselector
WORKDIR /opt/raspberry_extension_server

# Architecture automatically set by docker eg. linux/amd64, linux/arm/v7, linux/arm64
ARG TARGETPLATFORM

# ============================ Actual image from here ====================
FROM debian:stable-slim AS prod
WORKDIR /opt/raspberry_extension_server
ARG TARGETPLATFORM

COPY requirements.txt ./

## Install requirements
RUN apt update \
    && dpkg --configure -a \
    && apt install --no-install-recommends -y \
        python3 python3-pip python3-dev python3-setuptools gcc bluez git \
    && pip3 install -r requirements.txt --no-cache-dir --break-system-packages

## Install diyHue
COPY ./flaskUI/ /opt/raspberry_extension_server/flaskUI/
COPY ./ServerObjects/ /opt/raspberry_extension_server/ServerObjects/
COPY ./services/ /opt/raspberry_extension_server/services/
COPY ./configManager/ /opt/raspberry_extension_server/configManager/
COPY ./api.py /opt/raspberry_extension_server/
COPY ./githubInstall.sh /opt/raspberry_extension_server/

## Install the web interface
RUN curl -sL -A "Mozilla/5.0" https://github.com/hendriksen-mark/raspberry_extension_server_ui/releases/latest/download/raspberry_extension_server_ui-release.zip -o serverUI.zip \
    && if ! unzip -tq serverUI.zip > /dev/null; then \
         echo "Downloaded file is not a valid zip. Showing first 20 lines:"; \
         head -20 serverUI.zip; \
         exit 1; \
       fi \
    && mkdir serverUI \
    && unzip -qo serverUI.zip -d serverUI \
    && rm serverUI.zip \
    && mv serverUI/dist/index.html flaskUI/templates/ \
    && cp -r serverUI/dist/assets flaskUI/ \
    && rm -r serverUI

## Expose ports
EXPOSE 5002

CMD [ "python3", "-u", "/opt/raspberry_extension_server/api.py", "--docker" ]
