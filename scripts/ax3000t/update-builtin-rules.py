#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only

import datetime
import gzip
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import urllib.request


RESOURCES = Path(__file__).resolve().parent
SOURCES = {
    "adaway": ("AdAway", "https://raw.githubusercontent.com/AdAway/adaway.github.io/master/hosts.txt"),
    "adguard": ("AdGuard DNS", "https://adguardteam.github.io/AdGuardSDNSFilter/Filters/filter.txt"),
    "anti_ad": ("anti-AD", "https://raw.githubusercontent.com/privacy-protection-tools/anti-AD/master/anti-ad-domains.txt"),
    "yoyo": ("Yoyo", "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=nohtml&showintro=0&mimetype=plaintext"),
}


def normalize(domain):
    domain = domain.strip().lower().rstrip(".")
    if not re.fullmatch(r"(?:[a-z0-9_-]{1,63}\.)+[a-z0-9-]{2,63}", domain):
        return None
    try:
        ipaddress.ip_address(domain)
        return None
    except ValueError:
        return domain


def extract(name, content):
    domains = set()
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "!", "@@")):
            continue
        if name == "adguard":
            match = re.fullmatch(r"\|\|([^/\^$|]+)\^", line)
            candidate = match.group(1) if match else ""
        elif name == "adaway":
            fields = line.split()
            candidate = fields[1] if len(fields) >= 2 and fields[0] == "127.0.0.1" else ""
        else:
            candidate = line.split()[0]
        domain = normalize(candidate)
        if domain:
            domains.add(domain)
    return domains


def main():
    output = RESOURCES / "builtin-rules"
    output.mkdir(exist_ok=True)
    manifest = {"更新时间": datetime.datetime.now(datetime.timezone.utc).isoformat(), "来源": {}}
    merged = set()
    for name, (title, url) in SOURCES.items():
        request = urllib.request.Request(url, headers={"User-Agent": "AX3000T-firmware-rules"})
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
        domains = extract(name, raw.decode("utf-8"))
        if len(domains) < 1000:
            raise SystemExit(f"规则源数据异常：{title}，只取得 {len(domains)} 个域名。")
        # 插件备份使用倒序域名，启动时可直接还原并合并。
        reversed_domains = sorted(".".join(reversed(domain.split("."))) for domain in domains)
        backup = ("\n".join(reversed_domains) + "\n").encode("ascii")
        packed = gzip.compress(backup, compresslevel=9, mtime=0)
        filename = f"adb_list.{name}.gz"
        (output / filename).write_bytes(packed)
        manifest["来源"][name] = {
            "名称": title, "网址": url, "域名数": len(domains),
            "源文件SHA256": hashlib.sha256(raw).hexdigest(),
            "备份文件": filename, "备份SHA256": hashlib.sha256(packed).hexdigest(),
        }
        merged.update(domains)
        print(f"已预置 {title}：{len(domains)} 个域名。", flush=True)
    manifest["去重域名数"] = len(merged)
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
