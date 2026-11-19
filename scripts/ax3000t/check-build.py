#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only

import json
import gzip
import hashlib
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


ROOT = Path(__file__).resolve().parents[2]
DEVICE = "xiaomi_mi-router-ax3000t-stock"
REQUIRED = [
    "luci", "luci-ssl-openssl", "luci-theme-argon", "luci-app-mtwifi-cfg",
    "luci-app-firewall", "luci-app-opkg", "luci-app-upnp", "luci-app-ddns",
    "luci-app-adblock", "adblock", "luci-app-passwall2", "xray-core", "sing-box",
    "geoview", "chinadns-ng", "lyaml", "v2ray-geoip", "v2ray-geosite",
    "dnsmasq-full", "firewall",
    "iptables-mod-tproxy", "kmod-ipt-tproxy", "kmod-mt_wifi",
    "luci-i18n-base-zh-cn", "luci-i18n-firewall-zh-cn",
    "luci-i18n-opkg-zh-cn", "luci-i18n-mtwifi-cfg-zh-cn",
    "luci-i18n-passwall2-zh-cn", "luci-i18n-adblock-zh-cn",
    "luci-i18n-upnp-zh-cn", "luci-i18n-ddns-zh-cn",
]


def check_config():
    sources = json.loads((ROOT / "scripts/ax3000t/feeds.lock.json").read_text())
    preferred = {"passwall_packages": sources["passwall_packages"]["paths"],
                 "passwall2": ["luci-app-passwall2"]}
    for feed, names in preferred.items():
        for name in names:
            expected = ROOT / "feeds" / feed / name
            installed = list((ROOT / "package/feeds").glob(f"*/{name}"))
            if len(installed) != 1 or installed[0].resolve() != expected.resolve():
                raise SystemExit(f"软件源选择错误或存在重复组件：{name}")
    lines = (ROOT / ".config").read_text().splitlines()
    enabled = {line[:-2] for line in lines if line.endswith("=y")}
    target = f"CONFIG_TARGET_mediatek_mt7981_DEVICE_{DEVICE}"
    devices = {key for key in enabled if "_DEVICE_" in key and key.startswith("CONFIG_TARGET")}
    if devices != {target}:
        raise SystemExit(f"设备目标不符合 AX3000T 联发科 V1 原厂分区要求：{sorted(devices)}")
    missing = [name for name in REQUIRED if f"CONFIG_PACKAGE_{name}" not in enabled]
    if missing:
        raise SystemExit("以下必需软件包未选中：" + "、".join(missing))
    tls = {key for key in enabled if key.startswith("CONFIG_PACKAGE_libustream-")}
    if tls != {"CONFIG_PACKAGE_libustream-openssl"}:
        raise SystemExit("加密传输库必须统一使用 OpenSSL，避免安装文件冲突。")
    for symbol in ["CONFIG_LUCI_LANG_zh_Hans", "CONFIG_PACKAGE_dnsmasq_full_ipset",
                   "CONFIG_PACKAGE_luci-app-passwall2_Basic_Core_All",
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
    versions = {line.split()[0]: line.split()[-1]
                for line in manifests[0].read_text().splitlines() if line}
    for name, version in {"xray-core": "26.11.9", "sing-box": "1.14.4",
                          "luci-app-passwall2": "26.11.11"}.items():
        actual = versions.get(name, "")
        if actual != version and not actual.startswith(version + "-"):
            raise SystemExit(f"镜像中的代理组件版本不匹配：{name} {versions.get(name)}")
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
    # 直接解开最终镜像，检查双核心和预置规则，避免只验证构建配置。
    unpacker = next((ROOT / "staging_dir/host/bin" / name for name in
                     ["unsquashfs4", "unsquashfs"]
                     if (ROOT / "staging_dir/host/bin" / name).is_file()), None)
    if unpacker is None:
        raise SystemExit("缺少文件系统解包工具，不能检查预置规则。")
    with tempfile.TemporaryDirectory(prefix="ax3000t-image-check-") as temporary:
        temporary = Path(temporary)
        squashfs = temporary / "root.squashfs"
        with tarfile.open(image) as archive:
            member = next(member for member in archive.getmembers()
                          if Path(member.name).name == "root")
            squashfs.write_bytes(archive.extractfile(member).read())
        extracted = temporary / "rootfs"
        subprocess.run([str(unpacker), "-no-progress", "-d", str(extracted), str(squashfs)],
                       check=True, stdout=subprocess.DEVNULL)
        check_builtins(extracted)
    print(f"镜像检查通过：{image.name}，内核 {files['kernel']} 字节，根文件系统 {files['root']} 字节。")


def check_builtins(rootfs):
    for name in ["xray", "sing-box"]:
        binary = (rootfs / "usr/bin" / name).read_bytes()
        if binary[:4] != b"\x7fELF" or int.from_bytes(binary[18:20], "little") != 183:
            raise SystemExit(f"代理核心不是正确的 ARM64 程序：{name}")
    for name in ["geoip.dat", "geosite.dat"]:
        if (rootfs / "usr/share/v2ray" / name).stat().st_size < 10000:
            raise SystemExit(f"缺少预置地理分流数据：{name}")
    config = (rootfs / "etc/config/passwall2").read_text()
    for value in ["geosite:cn", "geoip:cn", "geoip:private", "geosite:gfw",
                  "geosite:geolocation-!cn", "geosite:category-ads-all"]:
        if value not in config:
            raise SystemExit(f"缺少国内通用分流配置：{value}")
    folder = rootfs / "usr/share/ax3000t/adblock"
    manifest = json.loads((folder / "manifest.json").read_text())
    for name in ["adaway", "adguard", "anti_ad", "yoyo"]:
        source = manifest["来源"][name]
        packed = (folder / source["备份文件"]).read_bytes()
        if hashlib.sha256(packed).hexdigest() != source["备份SHA256"]:
            raise SystemExit(f"固件内广告规则校验失败：{name}")
        if len(gzip.decompress(packed).splitlines()) != source["域名数"]:
            raise SystemExit(f"固件内广告规则数量不匹配：{name}")
    print("双核心、国内分流配置和四组离线广告规则已通过镜像内容检查。")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["config", "image"]:
        raise SystemExit("用法：check-build.py config 或 check-build.py image")
    check_config()
    if sys.argv[1] == "image":
        check_image()
