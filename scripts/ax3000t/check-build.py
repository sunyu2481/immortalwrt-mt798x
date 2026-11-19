#!/usr/bin/env python3

import json
from pathlib import Path
import subprocess
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[2]
DEVICE = "xiaomi_mi-router-ax3000t-stock"
REQUIRED = [
    "luci", "luci-ssl", "luci-theme-argon", "luci-app-mtwifi-cfg",
    "luci-app-firewall", "luci-app-opkg", "luci-app-upnp", "luci-app-ddns",
    "luci-app-adblock", "adblock", "luci-app-passwall2", "xray-core",
    "geoview", "chinadns-ng", "lyaml", "dnsmasq-full", "firewall",
    "iptables-mod-tproxy", "kmod-ipt-tproxy", "kmod-mt_wifi",
    "luci-i18n-base-zh-cn", "luci-i18n-firewall-zh-cn",
    "luci-i18n-opkg-zh-cn", "luci-i18n-mtwifi-cfg-zh-cn",
    "luci-i18n-passwall2-zh-cn", "luci-i18n-adblock-zh-cn",
    "luci-i18n-upnp-zh-cn", "luci-i18n-ddns-zh-cn",
]


def check_config():
    lines = (ROOT / ".config").read_text().splitlines()
    enabled = {line[:-2] for line in lines if line.endswith("=y")}
    target = f"CONFIG_TARGET_mediatek_mt7981_DEVICE_{DEVICE}"
    devices = {key for key in enabled if "_DEVICE_" in key and key.startswith("CONFIG_TARGET")}
    if devices != {target}:
        raise SystemExit(f"设备目标不符合 AX3000T 联发科 V1 原厂分区要求：{sorted(devices)}")
    missing = [name for name in REQUIRED if f"CONFIG_PACKAGE_{name}" not in enabled]
    if missing:
        raise SystemExit("以下必需软件包未选中：" + "、".join(missing))
    for symbol in ["CONFIG_LUCI_LANG_zh_Hans", "CONFIG_PACKAGE_dnsmasq_full_ipset",
                   "CONFIG_PACKAGE_luci-app-passwall2_Basic_Core_Xray",
                   "CONFIG_PACKAGE_luci-app-passwall2_Iptables_Transparent_Proxy"]:
        if symbol not in enabled:
            raise SystemExit(f"必需配置未启用：{symbol}")
    print(f"配置检查通过：唯一设备为 {DEVICE}，必需功能及中文语言包已选中。")


def check_image():
    output = ROOT / "bin/targets/mediatek/mt7981"
    images = list(output.glob(f"*{DEVICE}-squashfs-sysupgrade.bin"))
    if len(images) != 1:
        raise SystemExit("没有找到唯一的 AX3000T 原厂分区升级镜像。")
    image = images[0]
    manifests = list(output.glob(f"*{DEVICE}.manifest"))
    if len(manifests) != 1:
        raise SystemExit("缺少设备软件包清单，不能确认镜像包含必需功能。")
    packages = {line.split()[0] for line in manifests[0].read_text().splitlines() if line}
    missing = set(REQUIRED) - packages
    if missing:
        raise SystemExit("镜像缺少必需软件包：" + "、".join(sorted(missing)))
    with tarfile.open(image) as archive:
        files = {Path(member.name).name: member.size for member in archive.getmembers()
                 if member.isfile()}
    if not files.get("kernel") or not files.get("root"):
        raise SystemExit("升级镜像缺少内核或根文件系统。")
    # 原厂布局分别提供约 34 MiB 内核分区和 78 MiB 根分区，并预留坏块空间。
    if files["kernel"] > 30 * 1024 * 1024 or files["root"] > 68 * 1024 * 1024:
        raise SystemExit("镜像超过原厂分区的保守容量限制，请精简软件包后重新构建。")
    metadata = subprocess.check_output([
        str(ROOT / "staging_dir/host/bin/fwtool"), "-i", "-", str(image)
    ], text=True)
    supported = json.loads(metadata).get("supported_devices", [])
    if "xiaomi,mi-router-ax3000t-stock" not in supported:
        raise SystemExit(f"镜像设备元数据不匹配：{supported}")
    print(f"镜像检查通过：{image.name}，内核 {files['kernel']} 字节，根文件系统 {files['root']} 字节。")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["config", "image"]:
        raise SystemExit("用法：check-build.py config 或 check-build.py image")
    check_config()
    if sys.argv[1] == "image":
        check_image()
