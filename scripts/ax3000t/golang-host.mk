# 使用官方主机工具链编译代理源码，避免重复构建 Go 占用云端磁盘。
include $(TOPDIR)/rules.mk

PKG_NAME:=golang
PKG_VERSION:=1.27.4
PKG_RELEASE:=1
PKG_SOURCE:=go$(PKG_VERSION).linux-amd64.tar.gz
PKG_SOURCE_URL:=https://go.dev/dl/ https://dl.google.com/go/
PKG_HASH:=7226736c2339719cda28fbf3a54d71aa63bcefe376e98cef00034268dab24840
PKG_LICENSE:=BSD-3-Clause
PKG_LICENSE_FILES:=LICENSE
PKG_HOST_ONLY:=1

HOST_BUILD_DIR:=$(BUILD_DIR_HOST)/go-$(PKG_VERSION)
HOST_GO_ROOT:=$(STAGING_DIR_HOSTPKG)/lib/go-cross

include $(INCLUDE_DIR)/host-build.mk
include $(INCLUDE_DIR)/package.mk

define Package/golang
  SECTION:=lang
  CATEGORY:=Languages
  TITLE:=用于交叉编译的 Go 主机工具链
  BUILDONLY:=1
endef

# 官方主机工具链直接解包，保留原始二进制和源码，不套用旧版补丁。
define Host/Prepare
	tar -C "$(HOST_BUILD_DIR)" --strip-components=1 -xzf "$(DL_DIR)/$(PKG_SOURCE)"
endef

define Host/Configure
	$(HOST_BUILD_DIR)/bin/go version
endef

define Host/Compile
endef

define Host/Install
	$(INSTALL_DIR) $(HOST_GO_ROOT) $(STAGING_DIR_HOSTPKG)/bin
	$(CP) $(HOST_BUILD_DIR)/. $(HOST_GO_ROOT)/
	$(INSTALL_DIR) $(HOST_GO_ROOT)/openwrt
	$(INSTALL_BIN) ./files/go-gcc-helper $(HOST_GO_ROOT)/openwrt/
	$(LN) go-gcc-helper $(HOST_GO_ROOT)/openwrt/gcc
	$(LN) go-gcc-helper $(HOST_GO_ROOT)/openwrt/g++
	$(LN) ../lib/go-cross/bin/go $(STAGING_DIR_HOSTPKG)/bin/go
	$(LN) ../lib/go-cross/bin/gofmt $(STAGING_DIR_HOSTPKG)/bin/gofmt
endef

$(eval $(call HostBuild))
$(eval $(call BuildPackage,golang))
