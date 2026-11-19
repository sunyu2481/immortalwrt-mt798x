# AX3000T 联发科 V1 原厂分区固件

使用当前 `immortalwrt-mt798x` 源码构建，基础提交为
`740103d655bcee6da7bc3b49b1cfdfdee4cd5bb6`。目标设备是 MT7981、联发科交换机的
小米 AX3000T，保留原厂引导及分区。设备目标为
`xiaomi_mi-router-ax3000t-stock`。

配置保留仓库预设的联发科无线驱动、无线设置、硬件加速、IPv4/IPv6、
DHCP、PPPoE、网络防火墙、SSH、软件包管理、UPnP 和常用诊断工具，增加：

- 默认简体中文界面及所选 LuCI 应用的简体中文语言包。
- 默认 Argon 主题。
- Passwall2 与 Xray，支持该内核提供的 VLESS、VMess、Trojan、Shadowsocks、Hysteria2 等协议。
- Adblock 域名过滤，默认使用较轻量的 AdAway 和 Yoyo 规则。
- 动态域名设置及简体中文语言包。

代理节点和订阅由使用者在刷机后填写。Adblock 的规则需要首次联网下载；
域名过滤无法屏蔽同一域名提供的所有视频广告。AX3000T 内存为 256 MiB，
本配置只启用 Xray；如果需要其他代理内核，应单独选择后重新构建。

## 在 Codespaces 构建

在包含本配置的仓库分支创建 Codespace，选择 4 核、16 GB 内存、32 GB 磁盘。
容器基于 Ubuntu 22.04，安装编译依赖后自动获取固定版本的软件源并生成配置，
不会自动开始完整编译。

```sh
# 等待容器的初始化步骤结束后检查配置。
bash scripts/build-ax3000t.sh check

# 检查真实剩余空间，然后开始构建。
df -h .
bash scripts/build-ax3000t.sh build
```

首次完整构建要求至少 25 GiB 可用空间。如果 32 GB 机型实际剩余空间不足，
应使用容量更大的机器或其他构建服务。构建结束前应保持 Codespace 运行，
防止空闲超时停止机器。

GitHub 的免费额度按核心小时和 GB 月计算。GitHub Free 每月包含 120 核心小时，
相当于 4 核机器运行 30 小时；还包含 15 GB 月存储额度，已有 Codespaces 会共享这些额度。
超额后的 4 核计算费为每小时 0.36 美元，存储为每 GB 月 0.07 美元。
是否有剩余额度须在个人账单页面确认。停止机器结束计算计费，保留的磁盘仍计算存储用量。

官方说明：
[资源规格](https://docs.github.com/en/codespaces/about-codespaces/what-are-codespaces)、
[计费](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces)。

## 手动准备其他 Linux 环境

按本仓库说明和 `.devcontainer/Dockerfile` 安装依赖，使用普通 AMD64 用户执行：

```sh
bash scripts/build-ax3000t.sh prepare
bash scripts/build-ax3000t.sh build
```

准备脚本使用浅克隆固定所有软件源版本，不引用其他固件目录或预编译固件。
主机 Go 使用官方带 SHA256 校验的 1.27.4 工具链，以编译新版 Xray 和 GeoView；
内核、联发科驱动和软件包仍按本仓库的构建规则生成。第三方软件包定义中的
预编译资源沿用其上游获取方式。

原有 `.config` 会备份到 `.config.before-ax3000t`。配置后不要另行执行
`scripts/feeds update -a`，以免覆盖针对本分支的软件源适配；重新准备应继续使用准备脚本。

## 构建产物与验证

产物位于 `bin/targets/mediatek/mt7981/`，包括：

- `*xiaomi_mi-router-ax3000t-stock-squashfs-sysupgrade.bin`：现有兼容固件的升级镜像。
- `ax3000t-stock.sha256`：升级镜像校验值。
- `ax3000t-stock.diffconfig`：本次实际配置。
- `ax3000t-source-commit.txt`、`ax3000t-feeds.lock.json`：源码及软件源版本。
- 设备软件包清单及构建系统生成的其他文件。

脚本会检查设备选择、必需功能和中文语言包，并在编译成功后检查镜像软件包清单、
内核与根文件系统大小、设备元数据。原厂布局的内核和根文件系统分区分别约为
34 MiB、78 MiB；构建检查分别限制为 30 MiB、68 MiB，为坏块和可写配置保留余量。

刷机前在设备上确认实际型号、交换机及分区，并使用现有固件的镜像兼容性检查。
不能将扩大分区版或 AN8855 版镜像用于本配置的设备。跨版本升级建议备份设置后
不保留旧配置，避免旧网络和代理配置影响运行。

只有编译和镜像检查通过，仍不能替代设备上的启动、无线、上网、中文界面、
代理分流及去广告验证。构建环境无法执行实机验证。

## 已确认的设备情况

设备反馈的现有系统为 ImmortalWrt 25.12.2、内核 6.12.103，设备标识为
`xiaomi,mi-router-ax3000t`；`ubi_kernel` 和 `ubi` 分区分别为 34 MiB、78 MiB，
与本构建的原厂布局相符。

本源码采用旧内核及联发科驱动，镜像标识为 `xiaomi,mi-router-ax3000t-stock`。
两个系统的标识和网络驱动不同，升级前须在现有系统执行镜像兼容性检查，并确定
适用的跨分支升级流程。不要沿用现有系统的网络和无线配置。
本源码中无 `stock` 后缀的另一个镜像采用 112 MiB 布局，因此保留镜像标识的区分。
本次工作仅生成固件，不执行设备升级。
