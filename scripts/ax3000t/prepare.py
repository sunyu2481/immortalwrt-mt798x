#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only

import json
import os
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
RESOURCES = Path(__file__).resolve().parent


def run(*args, cwd=ROOT):
    subprocess.run(args, cwd=cwd, check=True)


def checkout_feed(name, source):
    path = ROOT / "feeds" / name
    if not path.exists():
        path.mkdir(parents=True)
        run("git", "init", "-q", str(path))
        run("git", "remote", "add", "origin", source["url"], cwd=path)
    if not (path / ".git").is_dir():
        raise SystemExit(f"软件源目录不是独立仓库，请先检查：{path}")
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=path, capture_output=True, text=True,
    )
    if head.returncode == 0:
        if head.stdout.strip() != source["revision"]:
            raise SystemExit(f"已有软件源版本不同，停止以保留现有工作：{path}")
        return
    print(f"获取固定版本的软件源：{name}", flush=True)
    run("git", "-c", "credential.helper=", "fetch", "--depth=1", "origin",
        source["revision"], cwd=path)
    run("git", "checkout", "-q", "--detach", "FETCH_HEAD", cwd=path)


def main():
    if os.geteuid() == 0:
        raise SystemExit("请使用普通用户准备并构建固件。")
    sources = json.loads((RESOURCES / "feeds.lock.json").read_text())
    for name, source in sources.items():
        checkout_feed(name, source)
        if source.get("paths"):
            path = ROOT / "feeds" / name
            run("git", "sparse-checkout", "init", "--cone", cwd=path)
            run("git", "sparse-checkout", "set", *source["paths"], cwd=path)

    # 保留当前源码的构建规则，仅替换主机 Go 的安装方法。
    shutil.copyfile(
        RESOURCES / "golang-host.mk",
        ROOT / "feeds/packages/lang/golang/golang/Makefile",
    )

    # 本分支的透明代理模块已同时提供套接字匹配，防火墙采用旧版规则。
    passwall = ROOT / "feeds/passwall2/luci-app-passwall2"
    makefile = passwall / "Makefile"
    text = makefile.read_text()
    for symbol in ["iptables-nft", "iptables-zz-legacy", "iptables-mod-socket"]:
        text = text.replace(f"\tselect PACKAGE_{symbol}\n", "")
    makefile.write_text(text)

    # 使第三方语言目录遵循本分支的语言命名，自动选中简体中文翻译。
    for old, new in [("zh-cn", "zh_Hans"), ("zh-tw", "zh_Hant")]:
        original = passwall / "po" / old
        translated = passwall / "po" / new
        if original.is_dir():
            if translated.is_symlink() and translated.resolve() == original.resolve():
                translated.unlink()
            original.rename(translated)

    feed_config = "".join(
        f"src-git {name} {source['url']}^{source['revision']}\n"
        for name, source in sources.items()
    )
    (ROOT / "feeds.conf").write_text(feed_config)
    run("./scripts/feeds", "update", "-i", "-a")
    run("./scripts/feeds", "install", "-a")
    run("./scripts/feeds", "install", "-f", "-p", "passwall_packages",
        "xray-core", "geoview", "chinadns-ng", "tcping",
        "v2ray-geoip", "v2ray-geosite")
    run("./scripts/feeds", "install", "-f", "-p", "passwall2", "luci-app-passwall2")

    defaults = ROOT / "files/etc/uci-defaults/zzz-ax3000t-defaults"
    defaults.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RESOURCES / "zzz-ax3000t-defaults", defaults)
    defaults.chmod(0o755)

    config = ROOT / ".config"
    if config.exists():
        backup = ROOT / ".config.before-ax3000t"
        if not backup.exists():
            shutil.copyfile(config, backup)
    profile = (ROOT / "defconfig/mt7981-ax3000t-stock.config").read_text()
    overridden = set(re.findall(r"^(?:# )?(CONFIG_\S+?)(?:=| is not set)", profile, re.M))
    base = (ROOT / "defconfig/mt7981-ax3000.config").read_text().splitlines()
    kept = []
    for line in base:
        match = re.match(r"^(?:# )?(CONFIG_\S+?)(?:=| is not set)", line)
        if match:
            key = match.group(1)
            if key in overridden or key.startswith("CONFIG_TARGET_DEVICE_"):
                continue
        kept.append(line)
    config.write_text("\n".join(kept) + "\n" + profile)
    run("make", "defconfig")
    run("python3", "scripts/ax3000t/check-build.py", "config")
    print("AX3000T 联发科 V1 原厂分区配置已准备完成。", flush=True)


if __name__ == "__main__":
    main()
