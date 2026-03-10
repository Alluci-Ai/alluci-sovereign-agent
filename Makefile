
# Alluci Sovereign Agent Makefile
# Packaging for Debian/RPi

APP_NAME = alluci-sovereign-agent
VERSION = 1.0.0
PKG_DIR = pkg_root_$(APP_NAME)
DEB_FILE = $(APP_NAME)_$(VERSION)_amd64.deb
PI_DEB_FILE = $(APP_NAME)_$(VERSION)_armhf.deb

all: build

build:
	@echo "Building frontend..."
	npm install && npm run build
	@echo "Backend dependencies are managed via install.sh"

clean:
	rm -rf $(PKG_DIR) *.deb dist

# Standard Linux .deb
deb: build
	@echo "Creating .deb package for amd64..."
	mkdir -p $(PKG_DIR)/usr/bin
	mkdir -p $(PKG_DIR)/usr/lib/$(APP_NAME)
	mkdir -p $(PKG_DIR)/etc/systemd/user
	
	# Copy files
	cp -r backend $(PKG_DIR)/usr/lib/$(APP_NAME)/
	cp -r dist $(PKG_DIR)/usr/lib/$(APP_NAME)/frontend
	cp service_templates/polytope.service $(PKG_DIR)/etc/systemd/user/alluci.service
	cp scripts/install.sh $(PKG_DIR)/usr/bin/alluci-install
	
	# Control file
	mkdir -p $(PKG_DIR)/DEBIAN
	echo "Package: $(APP_NAME)" > $(PKG_DIR)/DEBIAN/control
	echo "Version: $(VERSION)" >> $(PKG_DIR)/DEBIAN/control
	echo "Section: base" >> $(PKG_DIR)/DEBIAN/control
	echo "Priority: optional" >> $(PKG_DIR)/DEBIAN/control
	echo "Architecture: amd64" >> $(PKG_DIR)/DEBIAN/control
	echo "Maintainer: Alluci Team <support@alluci.ai>" >> $(PKG_DIR)/DEBIAN/control
	echo "Description: Alluci Sovereign Agent - Personal AI Stack" >> $(PKG_DIR)/DEBIAN/control
	
	dpkg-deb --build $(PKG_DIR) $(DEB_FILE)
	@echo "Created $(DEB_FILE)"

# Raspberry Pi .deb
deb-pi: build
	@echo "Creating .deb package for armhf (Raspberry Pi)..."
	# Similar to deb but with armhf arch and LITE_MODE hints
	mkdir -p $(PKG_DIR)/usr/bin
	mkdir -p $(PKG_DIR)/usr/lib/$(APP_NAME)
	mkdir -p $(PKG_DIR)/etc/systemd/user
	
	cp -r backend $(PKG_DIR)/usr/lib/$(APP_NAME)/
	cp -r dist $(PKG_DIR)/usr/lib/$(APP_NAME)/frontend
	cp service_templates/polytope.service $(PKG_DIR)/etc/systemd/user/alluci.service
	
	mkdir -p $(PKG_DIR)/DEBIAN
	echo "Package: $(APP_NAME)" > $(PKG_DIR)/DEBIAN/control
	echo "Version: $(VERSION)" >> $(PKG_DIR)/DEBIAN/control
	echo "Architecture: armhf" >> $(PKG_DIR)/DEBIAN/control
	echo "Maintainer: Alluci Team <support@alluci.ai>" >> $(PKG_DIR)/DEBIAN/control
	echo "Description: Alluci Sovereign Agent (Pi Lite Edition)" >> $(PKG_DIR)/DEBIAN/control
	
	# Add preinst/postinst scripts if needed to auto-enable LITE_MODE
	echo "#!/bin/bash" > $(PKG_DIR)/DEBIAN/postinst
	echo "echo \"LITE_MODE=true\" >> /usr/lib/$(APP_NAME)/.env" >> $(PKG_DIR)/DEBIAN/postinst
	chmod 555 $(PKG_DIR)/DEBIAN/postinst
	
	dpkg-deb --build $(PKG_DIR) $(PI_DEB_FILE)
	@echo "Created $(PI_DEB_FILE)"
